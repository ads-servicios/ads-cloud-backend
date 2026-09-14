from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Action, require_permission
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth import RoleCreate, RoleRead, RoleUpdate
from app.services import roles as roles_service

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleRead])
async def list_roles(
    _: User = Depends(require_permission("roles", Action.LIST)),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    roles = await roles_service.list_roles(db)
    return [roles_service.serialize_role(role) for role in roles]


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: int,
    _: User = Depends(require_permission("roles", Action.READ)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        role = await roles_service.get_role(db, role_id)
    except roles_service.RoleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found") from None
    return roles_service.serialize_role(role)


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    _: User = Depends(require_permission("roles", Action.CREATE)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        role = await roles_service.create_role(db, payload)
    except roles_service.RoleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    return roles_service.serialize_role(role)


@router.put("/{role_id}", response_model=RoleRead)
async def replace_role(
    role_id: int,
    payload: RoleUpdate,
    _: User = Depends(require_permission("roles", Action.EDIT)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        role = await roles_service.update_role(db, role_id, payload)
    except roles_service.RoleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found") from None
    except roles_service.RoleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except roles_service.RoleProtectedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    return roles_service.serialize_role(role)


@router.patch("/{role_id}", response_model=RoleRead)
async def patch_role(
    role_id: int,
    payload: RoleUpdate,
    _: User = Depends(require_permission("roles", Action.EDIT)),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        role = await roles_service.update_role(db, role_id, payload)
    except roles_service.RoleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found") from None
    except roles_service.RoleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except roles_service.RoleProtectedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    return roles_service.serialize_role(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    _: User = Depends(require_permission("roles", Action.DELETE)),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await roles_service.delete_role(db, role_id)
    except roles_service.RoleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found") from None
    except roles_service.RoleProtectedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
