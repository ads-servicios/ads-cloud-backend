from datetime import datetime, timezone

from app.core.config import settings


async def get_health_status() -> dict[str, object]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "timestamp": datetime.now(timezone.utc),
    }
