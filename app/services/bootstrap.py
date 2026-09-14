import logging

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.role_seed import ensure_system_roles
from app.services.users import ensure_bootstrap_admin

logger = logging.getLogger(__name__)


async def bootstrap_admin_if_needed() -> None:
    async with AsyncSessionLocal() as session:
        try:
            await ensure_system_roles(session)
        except Exception:
            logger.exception("System role seed skipped")
            return

        email = settings.bootstrap_admin_email.strip()
        password = settings.bootstrap_admin_password
        if not email or not password:
            return

        user = await ensure_bootstrap_admin(session, email=email, password=password)
        if user is not None:
            logger.info("Bootstrap administrator created: %s", user.email)
