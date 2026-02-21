from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models.bucket import Bucket
from backend.models.example import Example, ReviewStatus
from backend.schemas.example import BucketAssignment, ExampleDetail, ExampleListResponse, ExampleResponse

router = APIRouter()


@router.get("", response_model=ExampleListResponse)
async def list_examples(
    dataset_id: str | None = Query(None),
    bucket_id: str | None = Query(None),
    review_status: ReviewStatus | None = Query(None),
    min_score: float | None = Query(None),
    max_score: float | None = Query(None),
    sort_by: str = Query("aggregate_score"),
    sort_order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List examples with filters, sorting, and pagination."""
    query = select(Example)

    if dataset_id:
        query = query.where(Example.dataset_id == dataset_id)
    if bucket_id:
        query = query.where(Example.bucket_id == bucket_id)
    if review_status:
        query = query.where(Example.review_status == review_status)
    if min_score is not None:
        query = query.where(Example.aggregate_score >= min_score)
    if max_score is not None:
        query = query.where(Example.aggregate_score <= max_score)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Sort
    sort_col = getattr(Example, sort_by, Example.aggregate_score)
    if sort_col is not None:
        if sort_order == "desc":
            query = query.order_by(sort_col.desc().nullslast())
        else:
            query = query.order_by(sort_col.asc().nullsfirst())

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    examples = result.scalars().all()

    # Resolve bucket names
    items = []
    for ex in examples:
        resp = ExampleResponse.model_validate(ex)
        if ex.bucket_id:
            bucket_result = await db.execute(select(Bucket).where(Bucket.id == ex.bucket_id))
            bucket = bucket_result.scalar_one_or_none()
            if bucket:
                resp.bucket_name = bucket.display_name
        items.append(resp)

    return ExampleListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{example_id}", response_model=ExampleDetail)
async def get_example(example_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single example with all its scores."""
    result = await db.execute(
        select(Example).options(selectinload(Example.scores)).where(Example.id == example_id)
    )
    example = result.scalar_one_or_none()
    if not example:
        raise HTTPException(status_code=404, detail="Example not found")

    detail = ExampleDetail.model_validate(example)
    if example.bucket_id:
        bucket_result = await db.execute(select(Bucket).where(Bucket.id == example.bucket_id))
        bucket = bucket_result.scalar_one_or_none()
        if bucket:
            detail.bucket_name = bucket.display_name

    return detail


@router.patch("/{example_id}/bucket")
async def assign_bucket(
    example_id: str,
    assignment: BucketAssignment,
    db: AsyncSession = Depends(get_db),
):
    """Manually assign an example to a bucket."""
    result = await db.execute(select(Example).where(Example.id == example_id))
    example = result.scalar_one_or_none()
    if not example:
        raise HTTPException(status_code=404, detail="Example not found")

    example.bucket_id = assignment.bucket_id
    await db.commit()
    return {"status": "updated", "example_id": example_id, "bucket_id": assignment.bucket_id}
