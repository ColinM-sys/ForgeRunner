import json
import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.dataset import Dataset, DatasetStatus
from backend.models.example import Example
from backend.utils.jsonl import extract_fields, parse_jsonl_line, stream_jsonl


async def ingest_jsonl(
    db: AsyncSession,
    file_path: Path,
    filename: str,
    dataset_name: str | None = None,
) -> tuple[Dataset, list[str]]:
    """Parse and ingest a JSONL file into the database.

    Returns (dataset, errors).
    """
    name = dataset_name or Path(filename).stem
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    dataset = Dataset(name=name, filename=filename, file_path=str(file_path))
    db.add(dataset)
    await db.flush()

    errors = []
    valid_count = 0
    batch = []

    for line_number, line in stream_jsonl(file_path):
        data, error = parse_jsonl_line(line, line_number)

        if error:
            errors.append(error)
            continue

        if data is None:
            continue  # blank line

        fields = extract_fields(data)
        example = Example(
            dataset_id=dataset.id,
            line_number=line_number,
            **fields,
        )
        batch.append(example)
        valid_count += 1

        if len(batch) >= 500:
            db.add_all(batch)
            await db.flush()
            batch = []

    if batch:
        db.add_all(batch)
        await db.flush()

    dataset.total_examples = valid_count
    dataset.status = DatasetStatus.processing
    await db.commit()

    # Copy file to uploads directory for archival
    dest = upload_dir / f"{dataset.id}_{filename}"
    if file_path != dest:
        shutil.copy2(str(file_path), str(dest))
        dataset.file_path = str(dest)
        await db.commit()

    return dataset, errors
