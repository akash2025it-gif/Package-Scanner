from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.core.rbac import get_current_active_user, require_can_scan
from app.models import Product, Scan, User
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.schemas.scan import ScanListItemResponse, ScanSourceEnum, ScanStatusEnum

router = APIRouter(prefix="/products", tags=["Product Repository"])


@router.get("", response_model=APIResponse[PaginatedResponse[ProductResponse]])
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    brand: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lists registered products with filtering and pagination."""
    query = select(Product)

    if category:
        query = query.where(Product.category.ilike(f"%{category}%"))
    if brand:
        query = query.where(Product.brand.ilike(f"%{brand}%"))
    if search:
        p = f"%{search}%"
        query = query.where(
            or_(
                Product.name.ilike(p),
                Product.brand.ilike(p),
                Product.manufacturer_name.ilike(p),
                Product.barcode.ilike(p),
            )
        )

    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total_count = (await db.execute(count_stmt)).scalar_one()

    query = query.order_by(Product.name.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    products = result.scalars().all()

    # Query distinct batch numbers for these products
    p_ids = [p.id for p in products]
    batch_stmt = (
        select(Scan.product_id, Scan.batch_number)
        .where(
            Scan.product_id.in_(p_ids),
            Scan.batch_number.isnot(None),
            Scan.batch_number != "",
        )
        .distinct()
    )
    batch_res = await db.execute(batch_stmt)
    prod_batch_map = {}
    for p_id, b_num in batch_res.all():
        if p_id not in prod_batch_map:
            prod_batch_map[p_id] = []
        if b_num and b_num.strip() not in prod_batch_map[p_id]:
            prod_batch_map[p_id].append(b_num.strip())

    items = []
    for p in products:
        p_resp = ProductResponse.model_validate(p)
        p_batches = prod_batch_map.get(p.id, [])
        p_resp.known_batches = p_batches
        p_resp.batches_count = len(p_batches)
        items.append(p_resp)

    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=items,
            pagination=PaginationMeta(
                total=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        ),
    )


@router.post("", response_model=APIResponse[ProductResponse], status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_can_scan),
):
    """Registers a new packaged product in the repository."""
    product = Product(
        id=str(uuid.uuid4()),
        name=payload.name,
        brand=payload.brand,
        category=payload.category,
        manufacturer_name=payload.manufacturer_name,
        manufacturer_address=payload.manufacturer_address,
        country_of_origin=payload.country_of_origin or "India",
        barcode=payload.barcode,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    return APIResponse(
        success=True,
        message="Product registered successfully",
        data=ProductResponse.model_validate(product),
    )


@router.get("/{id}", response_model=APIResponse[ProductResponse])
async def get_product_by_id(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Fetches details of a product by ID."""
    result = await db.execute(select(Product).where(Product.id == id))
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException(f"Product {id} not found")

    batch_stmt = (
        select(Scan.batch_number)
        .where(
            Scan.product_id == id,
            Scan.batch_number.isnot(None),
            Scan.batch_number != "",
        )
        .distinct()
    )
    batch_res = await db.execute(batch_stmt)
    batches = [b for b in batch_res.scalars().all() if b and b.strip()]

    p_resp = ProductResponse.model_validate(product)
    p_resp.known_batches = batches
    p_resp.batches_count = len(batches)

    return APIResponse(success=True, data=p_resp)


@router.get("/{id}/scans", response_model=APIResponse[List[ScanListItemResponse]])
async def get_product_scans(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieves all historical compliance scans for a specific product."""
    result = await db.execute(select(Product).where(Product.id == id))
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException(f"Product {id} not found")

    scans_stmt = (
        select(Scan)
        .where(Scan.product_id == id)
        .options(
            selectinload(Scan.inspector),
            selectinload(Scan.declarations),
        )
        .order_by(Scan.created_at.desc())
    )
    scans_res = await db.execute(scans_stmt)
    scans = scans_res.scalars().all()

    items = []
    for s in scans:
        decls = s.declarations or []
        non_comp = sum(1 for d in decls if not d.is_compliant)
        verdict = "compliant" if non_comp == 0 and len(decls) > 0 else "non_compliant"

        items.append(
            ScanListItemResponse(
                id=s.id,
                product_id=product.id,
                product_name=product.name,
                product_brand=product.brand,
                product_category=product.category,
                inspector_id=s.inspector_id,
                inspector_name=s.inspector.name if s.inspector else None,
                source=ScanSourceEnum(s.source),
                status=ScanStatusEnum(s.status),
                location_name=s.location_name,
                region=s.inspector.region if s.inspector else None,
                total_declarations=len(decls),
                non_compliant_count=non_comp,
                overall_verdict=verdict,
                created_at=s.created_at,
            )
        )

    return APIResponse(success=True, data=items)
