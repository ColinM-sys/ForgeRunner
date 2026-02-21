import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.dataset import Dataset
from backend.schemas.dataset import DatasetResponse, UploadResponse
from backend.services.ingest import ingest_jsonl

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(file: UploadFile, db: AsyncSession = Depends(get_db)):
    """Upload a JSONL file for quality analysis."""
    if not file.filename or not file.filename.endswith(".jsonl"):
        raise HTTPException(status_code=400, detail="File must be a .jsonl file")

    # Write to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl", mode="wb") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        dataset, errors = await ingest_jsonl(db, tmp_path, file.filename)
        return UploadResponse(
            dataset_id=dataset.id,
            filename=file.filename,
            total_lines=dataset.total_examples + len(errors),
            valid_lines=dataset.total_examples,
            invalid_lines=len(errors),
            errors=errors[:20],  # Cap error list
        )
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("", response_model=list[DatasetResponse])
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """List all uploaded datasets."""
    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    datasets = result.scalars().all()
    return datasets


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single dataset by ID."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a dataset and all its examples."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    await db.delete(dataset)
    await db.commit()
    return {"status": "deleted", "dataset_id": dataset_id}
