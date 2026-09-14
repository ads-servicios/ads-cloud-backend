from collections import defaultdict

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.role import PermissionAction


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False


class ForceChangePasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)


class ScopeActions(BaseModel):
    scope: str = Field(min_length=1, max_length=64)
    actions: list[PermissionAction] = Field(min_length=1)

    @field_validator("scope")
    @classmethod
    def normalize_scope(cls, value: str) -> str:
        return value.strip().lower()


def permissions_from_role(role) -> list[ScopeActions]:
    if role is None:
        return []
    by_scope: dict[str, list[PermissionAction]] = defaultdict(list)
    for perm in getattr(role, "permissions", []) or []:
        by_scope[perm.scope].append(PermissionAction(perm.action))
    return [
        ScopeActions(scope=scope, actions=sorted(set(actions), key=lambda a: a.value))
        for scope, actions in sorted(by_scope.items())
    ]


class UserRead(BaseModel):
    id: int
    email: EmailStr
    role: str
    role_id: int
    is_active: bool
    must_change_password: bool
    permissions: list[ScopeActions] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def coerce_role_name(cls, data):
        if hasattr(data, "role_obj"):
            return {
                "id": data.id,
                "email": data.email,
                "role": data.role_obj.name if data.role_obj else "",
                "role_id": data.role_id,
                "is_active": data.is_active,
                "must_change_password": data.must_change_password,
                "permissions": permissions_from_role(data.role_obj),
            }
        return data


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = "common"
    is_active: bool = True


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    role: str | None = None
    is_active: bool | None = None


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str | None = None
    permissions: list[ScopeActions] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip().lower()


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = None
    permissions: list[ScopeActions] | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()


class RoleRead(BaseModel):
    id: int
    name: str
    description: str | None
    permissions: list[ScopeActions]

    model_config = {"from_attributes": True}
