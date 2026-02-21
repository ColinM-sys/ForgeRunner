from pydantic import BaseModel

from backend.models.review import ReviewAction


class ReviewCreate(BaseModel):
    action: ReviewAction
    notes: str | None = None


class BatchReviewCreate(BaseModel):
    example_ids: list[str]
    action: ReviewAction
    notes: str | None = None


class ReviewResponse(BaseModel):
    id: str
    example_id: str
    action: ReviewAction
    notes: str | None
    reviewed_at: str

    model_config = {"from_attributes": True}
