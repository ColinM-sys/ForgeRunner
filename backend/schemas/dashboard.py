from pydantic import BaseModel


class DashboardOverview(BaseModel):
    total_examples: int
    total_datasets: int
    approved_count: int
    rejected_count: int
    pending_count: int
    approval_rate: float
    average_score: float | None
    bucket_breakdown: list[dict]
    score_distribution: list[dict]
    engine_coverage: dict
