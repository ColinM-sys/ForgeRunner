from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas.export import ExportRequest, ExportResponse
from backend.services.export_service import export_examples

router = APIRouter()


@router.post("", response_model=ExportResponse)
async def create_export(request: ExportRequest, db: AsyncSession = Depends(get_db)):
    """Export filtered examples as JSONL."""
    file_path, count = await export_examples(db, request)
    return ExportResponse(
        filename=file_path.name,
        total_examples=count,
        download_url=f"/api/export/download/{file_path.name}",
    )


@router.get("/download/{filename}")
async def download_export(filename: str):
    """Download an exported JSONL file."""
    from pathlib import Path
    from backend.config import settings

    file_path = Path(settings.EXPORT_DIR) / filename
    if not file_path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/jsonl",
    )
