import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routers import buckets, dashboard, datasets, estimator, examples, export, review, scoring, sources
from backend.services.bucketing import ensure_default_buckets
from backend.services.scoring_orchestrator import ScoringOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting ForgeRunner...")
    await init_db()

    # Initialize scoring orchestrator
    orchestrator = ScoringOrchestrator()
    try:
        await orchestrator.initialize()
    except Exception as e:
        logger.warning(f"Scoring engines not fully initialized: {e}")
        logger.warning("Upload and browsing will work, but scoring requires GPU + dependencies")

    scoring.orchestrator = orchestrator
    sources.embedder = orchestrator.forge_embedder
    logger.info("ForgeRunner ready")

    yield

    # Shutdown
    await orchestrator.shutdown()
    logger.info("ForgeRunner stopped")


app = FastAPI(
    title="ForgeRunner",
    description="Unified Training Data Quality Dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router, prefix="/api/datasets", tags=["datasets"])
app.include_router(examples.router, prefix="/api/examples", tags=["examples"])
app.include_router(scoring.router, prefix="/api/scoring", tags=["scoring"])
app.include_router(buckets.router, prefix="/api/buckets", tags=["buckets"])
app.include_router(review.router, prefix="/api/review", tags=["review"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(estimator.router, prefix="/api/estimator", tags=["estimator"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ForgeRunner"}
