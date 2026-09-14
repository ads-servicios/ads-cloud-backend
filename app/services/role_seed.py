from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import ALL_PERMISSION_ACTIONS, PermissionAction, Role, RolePermission

DEFAULT_MATRIX: list[tuple[str, str | None, list[tuple[str, list[PermissionAction]]]]] = [
    (
        "administrator",
        "Full control",
        [
            ("users", list(ALL_PERMISSION_ACTIONS)),
            ("roles", list(ALL_PERMISSION_ACTIONS)),
            ("web_vehicles", list(ALL_PERMISSION_ACTIONS)),
        ],
    ),
    (
        "common",
        "Read-limited user",
        [
            ("users", [PermissionAction.READ]),
        ],
    ),
]


async def ensure_system_roles(db: AsyncSession) -> None:
    """Idempotent seed of administrator/common and their permission matrix."""
    for name, description, scopes in DEFAULT_MATRIX:
        result = await db.execute(
            select(Role).where(Role.name == name).options(selectinload(Role.permissions))
        )
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(name=name, description=description)
            db.add(role)
            await db.flush()
            for scope, actions in scopes:
                for action in actions:
                    db.add(RolePermission(role_id=role.id, scope=scope, action=action.value))
        else:
            existing = {(p.scope, p.action) for p in role.permissions}
            for scope, actions in scopes:
                for action in actions:
                    key = (scope, action.value)
                    if key not in existing:
                        db.add(RolePermission(role_id=role.id, scope=scope, action=action.value))
    await db.commit()


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    result = await db.execute(
        select(Role).where(Role.name == name).options(selectinload(Role.permissions))
    )
    return result.scalar_one_or_none()
