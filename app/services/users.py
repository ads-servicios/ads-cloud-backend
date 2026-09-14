from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token, hash_password, verify_password
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserUpdate
from app.services.role_seed import get_role_by_name


class UserConflictError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class RoleNotFoundError(Exception):
    pass


async def _resolve_role(db: AsyncSession, role_name: str) -> Role:
    role = await get_role_by_name(db, role_name.strip().lower())
    if role is None:
        raise RoleNotFoundError(f"Role '{role_name}' not found")
    return role


async def authenticate_user(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    result = await db.execute(
        select(User)
        .where(User.email == payload.email.lower())
        .options(selectinload(User.role_obj))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise InvalidCredentialsError("Invalid email or password")
    token = create_access_token(subject=str(user.id), role=user.role_obj.name)
    return TokenResponse(
        access_token=token,
        must_change_password=user.must_change_password,
    )


def _user_load_options():
    return selectinload(User.role_obj).selectinload(Role.permissions)


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(
        select(User).options(_user_load_options()).order_by(User.id)
    )
    return list(result.scalars().all())


async def get_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(
        select(User).where(User.id == user_id).options(_user_load_options())
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundError(f"User {user_id} not found")
    return user


async def create_user(db: AsyncSession, payload: UserCreate) -> User:
    email = payload.email.lower()
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise UserConflictError("Email already registered")

    role = await _resolve_role(db, payload.role)
    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        role_id=role.id,
        is_active=payload.is_active,
        must_change_password=True,
    )
    db.add(user)
    await db.commit()
    return await get_user(db, user.id)


async def update_user(db: AsyncSession, user_id: int, payload: UserUpdate) -> User:
    user = await get_user(db, user_id)
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        email = data["email"].lower()
        clash = await db.execute(select(User).where(User.email == email, User.id != user_id))
        if clash.scalar_one_or_none() is not None:
            raise UserConflictError("Email already registered")
        user.email = email
    if "password" in data and data["password"]:
        user.hashed_password = hash_password(data["password"])
    if "role" in data and data["role"] is not None:
        role = await _resolve_role(db, data["role"])
        user.role_id = role.id
        user.role_obj = role
    if "is_active" in data and data["is_active"] is not None:
        user.is_active = data["is_active"]
    await db.commit()
    return await get_user(db, user_id)


async def delete_user(db: AsyncSession, user_id: int) -> None:
    user = await get_user(db, user_id)
    await db.delete(user)
    await db.commit()


async def count_users(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(User))
    return int(result.scalar_one())


async def ensure_bootstrap_admin(db: AsyncSession, email: str, password: str) -> User | None:
    if await count_users(db) > 0:
        return None
    return await create_user(
        db,
        UserCreate(
            email=email,
            password=password,
            role="administrator",
            is_active=True,
        ),
    )


class PasswordChangeNotRequiredError(Exception):
    pass


async def force_change_password(db: AsyncSession, user: User, new_password: str) -> User:
    if not user.must_change_password:
        raise PasswordChangeNotRequiredError("Password change is not required")
    user.hashed_password = hash_password(new_password)
    user.must_change_password = False
    await db.commit()
    return await get_user(db, user.id)
