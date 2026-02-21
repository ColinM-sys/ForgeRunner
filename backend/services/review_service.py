from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.example import Example, ReviewStatus
from backend.models.review import Review, ReviewAction


async def review_example(
    db: AsyncSession,
    example_id: str,
    action: ReviewAction,
    notes: str | None = None,
) -> Review:
    """Record a review action on an example."""
    review = Review(example_id=example_id, action=action, notes=notes)
    db.add(review)

    # Update example review status
    result = await db.execute(select(Example).where(Example.id == example_id))
    example = result.scalar_one()

    status_map = {
        ReviewAction.approved: ReviewStatus.approved,
        ReviewAction.rejected: ReviewStatus.rejected,
        ReviewAction.needs_edit: ReviewStatus.needs_edit,
        ReviewAction.deferred: ReviewStatus.pending,
    }
    example.review_status = status_map[action]
    await db.commit()
    return review


async def batch_review(
    db: AsyncSession,
    example_ids: list[str],
    action: ReviewAction,
    notes: str | None = None,
) -> int:
    """Batch review multiple examples. Returns count of reviewed examples."""
    count = 0
    for eid in example_ids:
        result = await db.execute(select(Example).where(Example.id == eid))
        example = result.scalar_one_or_none()
        if example:
            await review_example(db, eid, action, notes)
            count += 1
    return count
