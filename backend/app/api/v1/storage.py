from fastapi import APIRouter, Response
from app.core.exceptions import NotFoundException
from app.services.storage import get_storage_service

router = APIRouter(prefix="/storage", tags=["Storage Service"])


@router.get("/{folder:path}")
async def get_stored_file(folder: str):
    """Retrieves and streams a file from the storage layer."""
    storage_service = get_storage_service()
    try:
        data = await storage_service.get_file_bytes(folder)
        lower_path = folder.lower()
        media_type = "application/octet-stream"
        if lower_path.endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"
        elif lower_path.endswith(".png"):
            media_type = "image/png"
        elif lower_path.endswith(".webp"):
            media_type = "image/webp"
        elif lower_path.endswith(".pdf"):
            media_type = "application/pdf"
        elif lower_path.endswith(".docx"):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        return Response(content=data, media_type=media_type)
    except Exception:
        raise NotFoundException(f"Stored object '{folder}' not found")
