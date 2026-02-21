from pydantic import BaseModel

from backend.models.example import ReviewStatus


class ExportRequest(BaseModel):
    dataset_ids: list[str] | None = None  # None = all datasets
    bucket_ids: list[str] | None = None  # None = all buckets
    review_status: ReviewStatus | None = ReviewStatus.approved
    min_score: float | None = None
    max_score: float | None = None


class ExportResponse(BaseModel):
    filename: str
    total_examples: int
    download_url: str
