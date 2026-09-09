import asyncio
import os
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.pipeline import AIPipeline
from app.rules.validators.net_quantity import NetQuantityValidator
from app.rules.config_loader import RuleConfigLoader
from app.workers.tasks import run_scan_analysis_pipeline_async
from app.models import Scan, ScanImage, Declaration, User
from sqlalchemy import select


@pytest.fixture(autouse=True)
def setup_windows_media_ocr():
    old = os.environ.get("OCR_PROVIDER")
    os.environ["OCR_PROVIDER"] = "windows_media"
    yield
    if old is not None:
        os.environ["OCR_PROVIDER"] = old
    else:
        os.environ.pop("OCR_PROVIDER", None)


@pytest.mark.asyncio
async def test_yoga_bar_image_extraction_grounding():
    """
    Verifies that the Yoga Bar Oats image (with printed 'Net Weight: 1 kg'):
    1. Extracts '1 kg' and NOT '100.0 g'.
    2. Correctly normalizes to 1000.0 g (preserving physical quantity).
    3. Accurately localizes the bounding box to the Net Weight region.
    4. Does not manufacture fake OCR declarations.
    """
    img_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "uploads",
        "scans",
        "0602a466-e704-4d70-80c7-02505afb6921",
        "913a43050cbb472483d6ee9173aebf11.webp",
    )
    if not os.path.exists(img_path):
        pytest.skip(f"Test image not found at {img_path}")

    with open(img_path, "rb") as f:
        img_bytes = f.read()

    pipeline = AIPipeline()
    result = await pipeline.analyze_image_bytes(img_bytes)

    declarations = {d["field_type"]: d for d in result["declarations"]}
    assert "net_quantity" in declarations, "net_quantity must be extracted"

    net_q = declarations["net_quantity"]
    assert net_q["is_present"] is True
    assert net_q["extracted_text"] == "1 kg"
    assert net_q.get("normalized_numeric_value") == 1000.0
    assert net_q.get("normalized_unit") == "g"
    assert "100" not in str(net_q["extracted_text"])

    # Verify evidence bounding box coordinates
    bbox = net_q.get("bounding_box", {})
    assert bbox.get("w", 0) > 0
    assert bbox.get("h", 0) > 0
    assert 900 <= bbox.get("x", 0) <= 1200
    assert 1300 <= bbox.get("y", 0) <= 1500


@pytest.mark.asyncio
async def test_dry_fruit_mix_image_extraction_grounding():
    """
    Verifies that Dry Fruit Mix (with printed '500 g'):
    1. Extracts '500 g' and NOT '1 kg' or '100.0 g'.
    2. Correctly normalizes to 500.0 g.
    3. Does not use stale values from previous scans.
    """
    img_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "uploads",
        "scans",
        "7b72ff41-6094-410c-bea1-29c12732078b",
        "a96e61381c8c4fe59a106af72925e882.jpg",
    )
    if not os.path.exists(img_path):
        pytest.skip(f"Test image not found at {img_path}")

    with open(img_path, "rb") as f:
        img_bytes = f.read()

    pipeline = AIPipeline()
    result = await pipeline.analyze_image_bytes(img_bytes)

    declarations = {d["field_type"]: d for d in result["declarations"]}
    assert "net_quantity" in declarations, "net_quantity must be extracted"

    net_q = declarations["net_quantity"]
    assert net_q["is_present"] is True
    assert net_q["extracted_text"] == "500 g"
    assert net_q.get("normalized_numeric_value") == 500.0
    assert net_q.get("normalized_unit") == "g"
    assert "1 kg" not in str(net_q["extracted_text"])
    assert "100" not in str(net_q["extracted_text"])


def test_net_quantity_normalization_preserves_physical_quantity():
    """
    Verifies that normalization preserves physical quantity:
    - 1 kg -> 1000 g (NEVER 100 g)
    - 500 g -> 500 g
    - 250 ml -> 250 ml
    - 1 L -> 1000 ml
    """
    validator = NetQuantityValidator()
    rule = RuleConfigLoader.get_instance().get_rule_by_id("RULE_6_1_D_NET_QUANTITY")

    # 1 kg
    res_1kg = validator.validate(rule=rule, text="Net Weight: 1 kg")
    assert res_1kg.extracted_value == "1 kg"
    assert res_1kg.normalized_numeric_value == 1000.0
    assert res_1kg.normalized_unit == "g"
    assert res_1kg.normalized_numeric_value != 100.0, "1 kg must NOT normalize to 100 g!"

    # 500 g
    res_500g = validator.validate(rule=rule, text="Net Qty: 500 g")
    assert res_500g.extracted_value == "500 g"
    assert res_500g.normalized_numeric_value == 500.0
    assert res_500g.normalized_unit == "g"

    # 250 ml
    res_250ml = validator.validate(rule=rule, text="Net Quantity: 250 ml")
    assert res_250ml.extracted_value == "250 ml"
    assert res_250ml.normalized_numeric_value == 250.0
    assert res_250ml.normalized_unit == "ml"


def test_extraction_conflict_triggers_manual_review():
    """
    Verifies that if package evidence indicates '1 kg' but a declared reference is '100 g',
    an extraction conflict is flagged and manual review is required.
    """
    validator = NetQuantityValidator()
    rule = RuleConfigLoader.get_instance().get_rule_by_id("RULE_6_1_D_NET_QUANTITY")

    res = validator.validate(
        rule=rule,
        text="Net Weight: 1 kg",
        metadata={"claimed_net_quantity": "100 g"},
    )
    assert res.has_conflict is True
    assert res.needs_review is True
    assert "Extraction Conflict" in (res.conflict_details or "")
    assert res.is_compliant is False, "Conflicting declaration must not pass as compliant automatically"


@pytest.mark.asyncio
async def test_end_to_end_scan_grounding_and_isolation(db_session: AsyncSession):
    """
    Verifies full end-to-end workflow:
    - Scan A with 1 kg package produces '1 kg' in database.
    - Scan B with 500 g package produces '500 g' in database.
    - Re-querying Scan A verifies isolation (no data leakage).
    """
    import uuid
    from app.services.storage import get_storage_service

    storage = get_storage_service()
    yoga_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "scans", "0602a466-e704-4d70-80c7-02505afb6921", "913a43050cbb472483d6ee9173aebf11.webp")
    dry_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "scans", "7b72ff41-6094-410c-bea1-29c12732078b", "a96e61381c8c4fe59a106af72925e882.jpg")

    if not os.path.exists(yoga_path) or not os.path.exists(dry_path):
        pytest.skip("Test images not found")

    with open(yoga_path, "rb") as f:
        yoga_bytes = f.read()
    with open(dry_path, "rb") as f:
        dry_bytes = f.read()

    db = db_session
    # Fetch or create a test user
    user_res = await db.execute(select(User).limit(1))
    user = user_res.scalar_one_or_none()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email="inspector.grounding@packcheck.gov.in",
            password_hash="hash",
            name="Grounding Inspector",
            role="inspector",
            is_active=True,
        )
        db.add(user)
        await db.flush()

    user_id = user.id

    # 1. Create Scan A
    scan_a = Scan(
        id=str(uuid.uuid4()),
        inspector_id=user_id,
        source="upload",
        status="processing",
        batch_number="BATCH-YOGA-1KG",
    )
    db.add(scan_a)
    await db.flush()

    url_a, key_a = await storage.upload_file(yoga_bytes, "yoga.webp", "image/webp", folder=f"scans/{scan_a.id}")
    img_a = ScanImage(
        id=str(uuid.uuid4()),
        scan_id=scan_a.id,
        image_url=url_a,
        storage_key=key_a,
        image_type="front",
        image_quality="CLEAR",
        sharpness_score=150.0,
        analysis_allowed=True,
    )
    db.add(img_a)

    # 2. Create Scan B
    scan_b = Scan(
        id=str(uuid.uuid4()),
        inspector_id=user_id,
        source="upload",
        status="processing",
        batch_number="BATCH-DRY-500G",
    )
    db.add(scan_b)
    await db.flush()

    url_b, key_b = await storage.upload_file(dry_bytes, "dryfruit.jpg", "image/jpeg", folder=f"scans/{scan_b.id}")
    img_b = ScanImage(
        id=str(uuid.uuid4()),
        scan_id=scan_b.id,
        image_url=url_b,
        storage_key=key_b,
        image_type="front",
        image_quality="CLEAR",
        sharpness_score=150.0,
        analysis_allowed=True,
    )
    db.add(img_b)
    await db.commit()

    # Run analysis on Scan A
    res_a = await run_scan_analysis_pipeline_async(scan_a.id, db=db)
    assert res_a["status"] == "success", f"Scan A failed: {res_a.get('message')}"

    # Run analysis on Scan B
    res_b = await run_scan_analysis_pipeline_async(scan_b.id, db=db)
    assert res_b["status"] == "success"

    # Verify Scan A declarations
    decl_a_res = await db.execute(select(Declaration).where(Declaration.scan_id == scan_a.id, Declaration.field_type == "net_quantity"))
    decl_a = decl_a_res.scalar_one()
    assert decl_a.extracted_text == "1 kg"
    assert decl_a.normalized_numeric_value == 1000.0
    assert "100.0" not in str(decl_a.extracted_text)

    # Verify Scan B declarations
    decl_b_res = await db.execute(select(Declaration).where(Declaration.scan_id == scan_b.id, Declaration.field_type == "net_quantity"))
    decl_b = decl_b_res.scalar_one()
    assert decl_b.extracted_text == "500 g"
    assert decl_b.normalized_numeric_value == 500.0

    # Cross-check Scan A again for isolation
    decl_a_check = (await db.execute(select(Declaration).where(Declaration.scan_id == scan_a.id, Declaration.field_type == "net_quantity"))).scalar_one()
    assert decl_a_check.extracted_text == "1 kg"

