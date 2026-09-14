from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Role, RolePermission, SYSTEM_ROLE_NAMES
from app.schemas.auth import RoleCreate, RoleUpdate, ScopeActions, permissions_from_role


class RoleConflictError(Exception):
    pass


class RoleNotFoundError(Exception):
    pass


class RoleProtectedError(Exception):
    pass


def serialize_role(role: Role) -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "permissions": permissions_from_role(role),
    }


async def list_roles(db: AsyncSession) -> list[Role]:
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).order_by(Role.id)
    )
    return list(result.scalars().all())


async def get_role(db: AsyncSession, role_id: int) -> Role:
    result = await db.execute(
        select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
    )
    role = result.scalar_one_or_none()
    if role is None:
        raise RoleNotFoundError(f"Role {role_id} not found")
    return role


def _apply_permissions(role: Role, permissions: list[ScopeActions]) -> None:
    role.permissions.clear()
    for item in permissions:
        for action in item.actions:
            role.permissions.append(
                RolePermission(scope=item.scope, action=action.value)
            )


async def create_role(db: AsyncSession, payload: RoleCreate) -> Role:
    existing = await db.execute(select(Role).where(Role.name == payload.name))
    if existing.scalar_one_or_none() is not None:
        raise RoleConflictError("Role name already exists")

    role = Role(name=payload.name, description=payload.description)
    _apply_permissions(role, payload.permissions)
    db.add(role)
    await db.commit()
    return await get_role(db, role.id)


async def update_role(db: AsyncSession, role_id: int, payload: RoleUpdate) -> Role:
    role = await get_role(db, role_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        new_name = data["name"]
        if new_name != role.name:
            if role.name in SYSTEM_ROLE_NAMES:
                raise RoleProtectedError("Cannot rename a system role")
            clash = await db.execute(select(Role).where(Role.name == new_name, Role.id != role_id))
            if clash.scalar_one_or_none() is not None:
                raise RoleConflictError("Role name already exists")
            role.name = new_name
    if "description" in data:
        role.description = data["description"]
    if "permissions" in data and data["permissions"] is not None:
        _apply_permissions(role, payload.permissions or [])
    await db.commit()
    return await get_role(db, role_id)


async def delete_role(db: AsyncSession, role_id: int) -> None:
    from sqlalchemy import func

    from app.models.user import User

    role = await get_role(db, role_id)
    if role.name in SYSTEM_ROLE_NAMES:
        raise RoleProtectedError("Cannot delete a system role")
    assigned = await db.execute(select(func.count()).select_from(User).where(User.role_id == role_id))
    if int(assigned.scalar_one()) > 0:
        raise RoleProtectedError("Cannot delete a role that is assigned to users")
    await db.delete(role)
    await db.commit()
