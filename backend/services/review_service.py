from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.example import Example, ReviewStatus
from backend.models.review import Review, ReviewAction


async def review_example(
    db: AsyncSession,
    example_id: str,
    action: ReviewAction,
    notes: str | None = None,
    example: Example | None = None,
) -> Review:
    """Record a review action on an example. `example`: the row, when the caller already has it
    (batch_review does), so it is not read twice."""
    review = Review(example_id=example_id, action=action, notes=notes)
    db.add(review)

    # Update example review status
    if example is None:
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
    # One read for the ids (in chunks, under SQLite's parameter limit), not one read per id plus
    # another inside review_example.
    unique = list(dict.fromkeys(example_ids))
    found: dict[str, Example] = {}
    for start in range(0, len(unique), 500):
        chunk = unique[start:start + 500]
        rows = await db.execute(select(Example).where(Example.id.in_(chunk)))
        found.update({ex.id: ex for ex in rows.scalars().all()})
    count = 0
    for eid in example_ids:
        example = found.get(eid)
        if example:
            await review_example(db, eid, action, notes, example=example)
            count += 1
    return count
