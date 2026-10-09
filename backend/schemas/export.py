from typing import Literal

from pydantic import BaseModel

from backend.models.example import ReviewStatus


class ExportRequest(BaseModel):
    dataset_ids: list[str] | None = None  # None = all datasets
    # "raw": each example's stored JSON, as it was imported (default, unchanged).
    # "aft": exactly {"messages": [...]} per line, the format Auto Fine Tuner trains on.
    format: Literal["raw", "aft"] = "raw"
    bucket_ids: list[str] | None = None  # None = all buckets
    review_status: ReviewStatus | None = ReviewStatus.approved
    min_score: float | None = None
    max_score: float | None = None


class ExportResponse(BaseModel):
    filename: str
    total_examples: int
    download_url: str
