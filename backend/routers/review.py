from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.example import Example
from backend.schemas.review import BatchReviewCreate, ReviewCreate
from backend.services.review_service import batch_review, review_example

router = APIRouter()


@router.post("/{example_id}")
async def review_single(
    example_id: str,
    data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
):
    """Review a single example (approve/reject/needs_edit)."""
    result = await db.execute(select(Example).where(Example.id == example_id))
    example = result.scalar_one_or_none()
    if not example:
        raise HTTPException(status_code=404, detail="Example not found")

    review = await review_example(db, example_id, data.action, data.notes)
    return {
        "status": "reviewed",
        "example_id": example_id,
        "action": data.action.value,
        "review_id": review.id,
    }


@router.post("/batch")
async def review_batch(data: BatchReviewCreate, db: AsyncSession = Depends(get_db)):
    """Batch review multiple examples."""
    count = await batch_review(db, data.example_ids, data.action, data.notes)
    return {
        "status": "reviewed",
        "count": count,
        "action": data.action.value,
    }
