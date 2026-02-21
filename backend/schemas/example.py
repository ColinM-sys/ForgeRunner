from datetime import datetime

from pydantic import BaseModel

from backend.models.example import ReviewStatus
from backend.schemas.score import ScoreResponse


class ExampleResponse(BaseModel):
    id: str
    dataset_id: str
    line_number: int
    system_prompt: str
    user_content: str
    assistant_content: str
    message_count: int
    char_count: int
    bucket_id: str | None
    bucket_name: str | None = None
    review_status: ReviewStatus
    aggregate_score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExampleDetail(ExampleResponse):
    raw_json: str
    scores: list[ScoreResponse] = []


class ExampleListResponse(BaseModel):
    items: list[ExampleResponse]
    total: int
    page: int
    page_size: int


class BucketAssignment(BaseModel):
    bucket_id: str
