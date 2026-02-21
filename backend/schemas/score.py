from datetime import datetime

from pydantic import BaseModel


class ScoreResponse(BaseModel):
    id: str
    engine_name: str
    score_type: str
    score_value: float
    details: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScoreResult(BaseModel):
    """Result from a scoring engine for one example."""
    example_id: str
    engine_name: str
    score_type: str
    score_value: float
    raw_value: dict = {}
    details: str | None = None
