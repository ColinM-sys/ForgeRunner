import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.bucket import Bucket
from backend.models.example import Example
from backend.schemas.bucket import BucketCreate, BucketResponse
from backend.services.bucketing import ensure_default_buckets

router = APIRouter()


@router.get("", response_model=list[BucketResponse])
async def list_buckets(db: AsyncSession = Depends(get_db)):
    """List all bucket types with example counts."""
    await ensure_default_buckets(db)

    result = await db.execute(
        select(Bucket, func.count(Example.id).label("count"))
        .outerjoin(Example, Example.bucket_id == Bucket.id)
        .group_by(Bucket.id)
        .order_by(Bucket.name)
    )
    rows = result.all()

    return [
        BucketResponse(
            id=bucket.id,
            name=bucket.name,
            display_name=bucket.display_name,
            description=bucket.description,
            is_system=bucket.is_system,
            color=bucket.color,
            example_count=count,
        )
        for bucket, count in rows
    ]


@router.post("", response_model=BucketResponse)
async def create_bucket(data: BucketCreate, db: AsyncSession = Depends(get_db)):
    """Create a custom bucket type."""
    existing = await db.execute(select(Bucket).where(Bucket.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Bucket '{data.name}' already exists")

    bucket = Bucket(
        name=data.name,
        display_name=data.display_name,
        description=data.description,
        color=data.color,
        is_system=False,
        detection_rules=json.dumps(data.detection_rules),
    )
    db.add(bucket)
    await db.commit()

    return BucketResponse(
        id=bucket.id,
        name=bucket.name,
        display_name=bucket.display_name,
        description=bucket.description,
        is_system=bucket.is_system,
        color=bucket.color,
        example_count=0,
    )
