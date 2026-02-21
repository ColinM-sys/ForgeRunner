from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.bucket import Bucket
from backend.models.dataset import Dataset
from backend.models.example import Example, ReviewStatus
from backend.models.score import Score


async def get_dashboard_overview(db: AsyncSession) -> dict:
    """Get aggregated stats for the dashboard."""
    # Total examples
    total_result = await db.execute(select(func.count(Example.id)))
    total_examples = total_result.scalar() or 0

    # Total datasets
    datasets_result = await db.execute(select(func.count(Dataset.id)))
    total_datasets = datasets_result.scalar() or 0

    # Review status counts
    approved_result = await db.execute(
        select(func.count(Example.id)).where(Example.review_status == ReviewStatus.approved)
    )
    approved_count = approved_result.scalar() or 0

    rejected_result = await db.execute(
        select(func.count(Example.id)).where(Example.review_status == ReviewStatus.rejected)
    )
    rejected_count = rejected_result.scalar() or 0

    pending_result = await db.execute(
        select(func.count(Example.id)).where(Example.review_status == ReviewStatus.pending)
    )
    pending_count = pending_result.scalar() or 0

    # Average score
    avg_result = await db.execute(
        select(func.avg(Example.aggregate_score)).where(Example.aggregate_score.isnot(None))
    )
    average_score = avg_result.scalar()

    # Bucket breakdown
    bucket_query = (
        select(Bucket.name, Bucket.display_name, Bucket.color, func.count(Example.id).label("count"))
        .outerjoin(Example, Example.bucket_id == Bucket.id)
        .group_by(Bucket.id)
    )
    bucket_result = await db.execute(bucket_query)
    bucket_breakdown = [
        {"name": row.name, "display_name": row.display_name, "color": row.color, "count": row.count}
        for row in bucket_result
    ]

    # Score distribution (histogram bins)
    score_distribution = []
    if total_examples > 0:
        for i in range(10):
            low = i * 0.1
            high = (i + 1) * 0.1
            count_result = await db.execute(
                select(func.count(Example.id)).where(
                    Example.aggregate_score >= low,
                    Example.aggregate_score < high if i < 9 else Example.aggregate_score <= high,
                )
            )
            count = count_result.scalar() or 0
            score_distribution.append({"range": f"{low:.1f}-{high:.1f}", "count": count})

    # Engine coverage
    engine_result = await db.execute(
        select(Score.engine_name, func.count(func.distinct(Score.example_id))).group_by(Score.engine_name)
    )
    engine_coverage = {row[0]: row[1] for row in engine_result}

    approval_rate = (approved_count / total_examples * 100) if total_examples > 0 else 0.0

    return {
        "total_examples": total_examples,
        "total_datasets": total_datasets,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "pending_count": pending_count,
        "approval_rate": round(approval_rate, 1),
        "average_score": round(average_score, 3) if average_score else None,
        "bucket_breakdown": bucket_breakdown,
        "score_distribution": score_distribution,
        "engine_coverage": engine_coverage,
    }
