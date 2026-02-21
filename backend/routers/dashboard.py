from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas.dashboard import DashboardOverview
from backend.services.stats import get_dashboard_overview

router = APIRouter()


@router.get("/overview", response_model=DashboardOverview)
async def dashboard_overview(db: AsyncSession = Depends(get_db)):
    """Get aggregated dashboard statistics."""
    data = await get_dashboard_overview(db)
    return DashboardOverview(**data)
