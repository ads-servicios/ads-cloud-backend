from fastapi import APIRouter

from app.controllers.health_controller import get_health_status
from app.schemas.health import HealthResponse


router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check() -> dict[str, object]:
    return await get_health_status()
