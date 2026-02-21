from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.example import Example, ReviewStatus
from backend.schemas.export import ExportRequest
from backend.utils.jsonl import write_jsonl


async def export_examples(db: AsyncSession, request: ExportRequest) -> tuple[Path, int]:
    """Export filtered examples as a JSONL file. Returns (file_path, count)."""
    query = select(Example)

    if request.dataset_ids:
        query = query.where(Example.dataset_id.in_(request.dataset_ids))

    if request.bucket_ids:
        query = query.where(Example.bucket_id.in_(request.bucket_ids))

    if request.review_status:
        query = query.where(Example.review_status == request.review_status)

    if request.min_score is not None:
        query = query.where(Example.aggregate_score >= request.min_score)

    if request.max_score is not None:
        query = query.where(Example.aggregate_score <= request.max_score)

    query = query.order_by(Example.dataset_id, Example.line_number)

    result = await db.execute(query)
    examples = result.scalars().all()

    export_dir = Path(settings.EXPORT_DIR)
    export_dir.mkdir(parents=True, exist_ok=True)

    import uuid
    filename = f"export_{uuid.uuid4().hex[:8]}.jsonl"
    file_path = export_dir / filename

    raw_jsons = [ex.raw_json for ex in examples]
    write_jsonl(file_path, raw_jsons)

    return file_path, len(examples)
