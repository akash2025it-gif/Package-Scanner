from fastapi import APIRouter
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.automation_config import router as automation_config_router
from app.api.v1.batches import router as batches_router
from app.api.v1.products import router as products_router
from app.api.v1.reports import router as reports_router
from app.api.v1.scans import check_image_quality, router as scans_router
from app.api.v1.storage import router as storage_router
from app.api.v1.users import router as users_router
from app.schemas.common import APIResponse

api_router = APIRouter()

# Alias for image quality checking
api_router.add_api_route("/images/quality-check", check_image_quality, methods=["POST"], tags=["Compliance Scans"])

# Health check
@api_router.get("/health", tags=["Health"])
async def health_check():
    return APIResponse(
        success=True,
        message="PackCheck API is operational",
        data={
            "service": "PackCheck Compliance Engine",
            "version": "1.0.0",
            "status": "healthy",
        },
    )

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(scans_router)
api_router.include_router(batches_router)
api_router.include_router(reports_router)
api_router.include_router(products_router)
api_router.include_router(analytics_router)
api_router.include_router(storage_router)
api_router.include_router(automation_config_router)
