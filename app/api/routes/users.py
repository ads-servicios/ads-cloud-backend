from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Action, require_permission
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth import UserCreate, UserRead, UserUpdate
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def list_users(
    _: User = Depends(require_permission("users", Action.LIST)),
    db: AsyncSession = Depends(get_db_session),
) -> list[User]:
    return await users_service.list_users(db)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    _: User = Depends(require_permission("users", Action.READ)),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    try:
        return await users_service.get_user(db, user_id)
    except users_service.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from None


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    _: User = Depends(require_permission("users", Action.CREATE)),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    try:
        return await users_service.create_user(db, payload)
    except users_service.UserConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except users_service.RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@router.put("/{user_id}", response_model=UserRead)
async def replace_user(
    user_id: int,
    payload: UserUpdate,
    _: User = Depends(require_permission("users", Action.EDIT)),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    try:
        return await users_service.update_user(db, user_id, payload)
    except users_service.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from None
    except users_service.UserConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except users_service.RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@router.patch("/{user_id}", response_model=UserRead)
async def patch_user(
    user_id: int,
    payload: UserUpdate,
    _: User = Depends(require_permission("users", Action.EDIT)),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    try:
        return await users_service.update_user(db, user_id, payload)
    except users_service.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from None
    except users_service.UserConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except users_service.RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    _: User = Depends(require_permission("users", Action.DELETE)),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await users_service.delete_user(db, user_id)
    except users_service.UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from None
