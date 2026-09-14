from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


class ServiceType(str, Enum):
    vehicles_stock = "vehicles_stock"
    mechanics_workshop = "mechanics_workshop"
    auction = "auction"
    other = "other"


class ContactRequest(BaseModel):
    full_name: str
    email: EmailStr
    service_type: ServiceType
    message: str
    privacy_policy_acceptance: bool

    @field_validator("full_name", "message")
    @classmethod
    def strip_and_require_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "all required fields must be completed"
            raise ValueError(msg)
        return stripped


class ContactSuccessResponse(BaseModel):
    status: str = Field(examples=["email sent"])


class ContactErrorResponse(BaseModel):
    message: str
