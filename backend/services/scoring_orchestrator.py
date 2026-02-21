import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import async_session
from backend.engines.cleanlab_engine import CleanlabEngine
from backend.engines.forge_embedder_engine import ForgeEmbedderEngine
from backend.models.dataset import Dataset, DatasetStatus
from backend.models.example import Example
from backend.models.score import Score
from backend.schemas.score import ScoreResult
from backend.services.bucketing import auto_bucket_dataset

logger = logging.getLogger(__name__)


class ScoringJobStatus:
    def __init__(self, job_id: str, dataset_id: str):
        self.job_id = job_id
        self.dataset_id = dataset_id
        self.status = "pending"  # pending, running, completed, error
        self.progress = 0.0
        self.current_engine = ""
        self.error = None
        self.started_at = None
        self.completed_at = None


# In-memory job tracking (single-user, no need for Redis)
_jobs: dict[str, ScoringJobStatus] = {}


def get_job_status(job_id: str) -> ScoringJobStatus | None:
    return _jobs.get(job_id)


class ScoringOrchestrator:
    """Coordinates all scoring engines against a dataset."""

    def __init__(self):
        self.forge_embedder = ForgeEmbedderEngine()
        self.cleanlab = CleanlabEngine()
        self._initialized = False

    async def initialize(self):
        """Initialize all engines."""
        await self.forge_embedder.initialize()
        await self.cleanlab.initialize()
        self._initialized = True
        logger.info("Scoring orchestrator initialized")

    async def start_scoring(self, dataset_id: str) -> str:
        """Start a scoring job in the background. Returns job_id."""
        job_id = str(uuid.uuid4())
        job = ScoringJobStatus(job_id, dataset_id)
        _jobs[job_id] = job

        asyncio.create_task(self._run_scoring(job))
        return job_id

    async def _run_scoring(self, job: ScoringJobStatus):
        """Run all scoring engines against the dataset."""
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)

        try:
            async with async_session() as db:
                # Load examples
                result = await db.execute(
                    select(Example).where(Example.dataset_id == job.dataset_id)
                )
                examples = result.scalars().all()

                if not examples:
                    job.status = "error"
                    job.error = "No examples found in dataset"
                    return

                example_dicts = [
                    {
                        "id": ex.id,
                        "system_prompt": ex.system_prompt,
                        "user_content": ex.user_content,
                        "assistant_content": ex.assistant_content,
                    }
                    for ex in examples
                ]

                # Step 1: ForgeEmbedder (must run first - produces embeddings)
                job.current_engine = "forge_embedder"
                job.progress = 0.1
                logger.info(f"Running ForgeEmbedder on {len(examples)} examples...")

                forge_results = await self.forge_embedder.score_batch(example_dicts)
                await self._save_scores(db, forge_results)
                job.progress = 0.4

                # Get cached embeddings for Cleanlab
                import numpy as np
                from pathlib import Path
                import hashlib

                cache_key = hashlib.md5(
                    f"{settings.EMBEDDING_MODEL}_{len(example_dicts)}".encode()
                ).hexdigest()
                cache_path = Path(settings.EMBEDDING_CACHE_DIR) / f"{cache_key}.npy"
                embeddings = np.load(str(cache_path)) if cache_path.exists() else None

                # Step 2: Cleanlab (uses embeddings from ForgeEmbedder)
                job.current_engine = "cleanlab"
                job.progress = 0.5
                logger.info(f"Running Cleanlab on {len(examples)} examples...")

                cleanlab_results = await self.cleanlab.score_batch(example_dicts, embeddings)
                await self._save_scores(db, cleanlab_results)
                job.progress = 0.7

                # Step 3: Compute aggregate scores
                job.current_engine = "aggregation"
                job.progress = 0.8
                await self._compute_aggregates(db, job.dataset_id)

                # Step 4: Auto-bucketing
                job.current_engine = "bucketing"
                job.progress = 0.9
                await auto_bucket_dataset(db, job.dataset_id)

                # Mark dataset as scored
                ds_result = await db.execute(
                    select(Dataset).where(Dataset.id == job.dataset_id)
                )
                dataset = ds_result.scalar_one()
                dataset.status = DatasetStatus.scored
                await db.commit()

                job.status = "completed"
                job.progress = 1.0
                job.completed_at = datetime.now(timezone.utc)
                logger.info(f"Scoring completed for dataset {job.dataset_id}")

        except Exception as e:
            logger.error(f"Scoring failed: {e}", exc_info=True)
            job.status = "error"
            job.error = str(e)

            try:
                async with async_session() as db:
                    ds_result = await db.execute(
                        select(Dataset).where(Dataset.id == job.dataset_id)
                    )
                    dataset = ds_result.scalar_one_or_none()
                    if dataset:
                        dataset.status = DatasetStatus.error
                        await db.commit()
            except Exception:
                pass

    async def _save_scores(self, db: AsyncSession, results: list[ScoreResult]):
        """Save scoring results to the database."""
        batch = []
        for r in results:
            score = Score(
                example_id=r.example_id,
                engine_name=r.engine_name,
                score_type=r.score_type,
                score_value=r.score_value,
                raw_value=json.dumps(r.raw_value),
                details=r.details,
            )
            batch.append(score)

            if len(batch) >= 500:
                db.add_all(batch)
                await db.flush()
                batch = []

        if batch:
            db.add_all(batch)
            await db.flush()
        await db.commit()

    async def _compute_aggregates(self, db: AsyncSession, dataset_id: str):
        """Compute weighted aggregate scores for all examples."""
        result = await db.execute(
            select(Example).where(Example.dataset_id == dataset_id)
        )
        examples = result.scalars().all()

        for example in examples:
            scores_result = await db.execute(
                select(Score).where(Score.example_id == example.id)
            )
            scores = scores_result.scalars().all()

            if not scores:
                continue

            # Average all score values (equal weight for MVP)
            score_values = [s.score_value for s in scores]
            example.aggregate_score = sum(score_values) / len(score_values)

        await db.commit()

    async def shutdown(self):
        await self.forge_embedder.shutdown()
        await self.cleanlab.shutdown()
