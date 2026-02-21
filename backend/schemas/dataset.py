from datetime import datetime

from pydantic import BaseModel

from backend.models.dataset import DatasetStatus


class DatasetCreate(BaseModel):
    name: str


class DatasetResponse(BaseModel):
    id: str
    name: str
    filename: str
    total_examples: int
    status: DatasetStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetDetail(DatasetResponse):
    score_summary: dict | None = None
    bucket_breakdown: dict | None = None


class UploadResponse(BaseModel):
    dataset_id: str
    filename: str
    total_lines: int
    valid_lines: int
    invalid_lines: int
    errors: list[str]
