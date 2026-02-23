from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.dataset import Dataset
from backend.services.scoring_orchestrator import ScoringOrchestrator, get_job_status

router = APIRouter()

# Singleton orchestrator (initialized in app lifespan)
orchestrator: ScoringOrchestrator | None = None


def get_orchestrator() -> ScoringOrchestrator:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Scoring engines not initialized")
    return orchestrator


@router.post("/start/{dataset_id}")
async def start_scoring(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    orch: ScoringOrchestrator = Depends(get_orchestrator),
):
    """Start a scoring job for a dataset."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    job_id = await orch.start_scoring(dataset_id)
    return {"job_id": job_id, "dataset_id": dataset_id, "status": "started"}


@router.post("/reaggregate/{dataset_id}")
async def reaggregate(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    orch: ScoringOrchestrator = Depends(get_orchestrator),
):
    """Recalculate aggregate scores without re-running engines."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    await orch._compute_aggregates(db, dataset_id)
    return {"status": "reaggregated", "dataset_id": dataset_id}


@router.get("/status/{job_id}")
async def scoring_status(job_id: str):
    """Check the status of a scoring job."""
    job = get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.job_id,
        "dataset_id": job.dataset_id,
        "status": job.status,
        "progress": job.progress,
        "current_engine": job.current_engine,
        "error": job.error,
    }
