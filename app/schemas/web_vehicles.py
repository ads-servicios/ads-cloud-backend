from datetime import date
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.web_vehicle import (
    VehicleCurrency,
    VehicleDriveType,
    VehicleFuelType,
    VehicleSaleStatus,
)
from app.services.web_vehicle_media import ImageUpload, public_urls_for_keys


class WebVehicleImageInput(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(default="application/octet-stream", alias="contentType")
    data: str = Field(min_length=1)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("filename")
    @classmethod
    def strip_filename(cls, value: str) -> str:
        return value.strip()


def _coerce_images(value: Any) -> list[str | ImageUpload]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("images must be a list")
    out: list[str | ImageUpload] = []
    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned:
                out.append(cleaned)
            continue
        if isinstance(item, ImageUpload):
            out.append(item)
            continue
        if isinstance(item, dict):
            parsed = WebVehicleImageInput.model_validate(item)
            out.append(
                ImageUpload(
                    filename=parsed.filename,
                    content_type=parsed.content_type,
                    data=parsed.data,
                )
            )
            continue
        if isinstance(item, WebVehicleImageInput):
            out.append(
                ImageUpload(
                    filename=item.filename,
                    content_type=item.content_type,
                    data=item.data,
                )
            )
            continue
        raise ValueError("images items must be stock keys or upload objects")
    return out


class WebVehicleBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    slug: str = Field(min_length=1, max_length=160)
    brand: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    year: int
    odometer: int = Field(ge=0)
    price: float = Field(ge=0)
    currency: VehicleCurrency
    sale_status: VehicleSaleStatus = Field(alias="saleStatus")
    motor_type: str = Field(alias="motorType", min_length=1, max_length=120)
    drive_type: VehicleDriveType = Field(alias="driveType")
    fuel_type: VehicleFuelType = Field(alias="fuelType")
    first_registration_date: date = Field(alias="firstRegistrationDate")
    images: Annotated[list[str | ImageUpload], Field(default_factory=list)]
    rebu: bool = False

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("title", "description", "slug", "brand", "model", "motor_type")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("images", mode="before")
    @classmethod
    def normalize_images(cls, value: Any) -> list[str | ImageUpload]:
        return _coerce_images(value)

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        if value < 1000 or value > 9999:
            raise ValueError("Year must be a 4-digit integer")
        return value


class WebVehicleCreate(WebVehicleBase):
    pass


class WebVehicleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    slug: str | None = Field(default=None, min_length=1, max_length=160)
    brand: str | None = Field(default=None, min_length=1, max_length=120)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    year: int | None = None
    odometer: int | None = Field(default=None, ge=0)
    price: float | None = Field(default=None, ge=0)
    currency: VehicleCurrency | None = None
    sale_status: VehicleSaleStatus | None = Field(default=None, alias="saleStatus")
    motor_type: str | None = Field(default=None, alias="motorType", min_length=1, max_length=120)
    drive_type: VehicleDriveType | None = Field(default=None, alias="driveType")
    fuel_type: VehicleFuelType | None = Field(default=None, alias="fuelType")
    first_registration_date: date | None = Field(default=None, alias="firstRegistrationDate")
    images: list[str | ImageUpload] | None = None
    rebu: bool | None = None

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("title", "description", "slug", "brand", "model", "motor_type")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("images", mode="before")
    @classmethod
    def normalize_optional_images(cls, value: Any) -> list[str | ImageUpload] | None:
        if value is None:
            return None
        return _coerce_images(value)

    @field_validator("year")
    @classmethod
    def validate_optional_year(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 1000 or value > 9999:
            raise ValueError("Year must be a 4-digit integer")
        return value


class WebVehiclePublic(BaseModel):
    uuid: str
    uid: int
    slug: str
    title: str
    description: str
    brand: str
    model: str
    year: int
    odometer: int
    price: float
    currency: VehicleCurrency
    sale_status: VehicleSaleStatus = Field(alias="saleStatus")
    motor_type: str = Field(alias="motorType")
    drive_type: VehicleDriveType = Field(alias="driveType")
    fuel_type: VehicleFuelType = Field(alias="fuelType")
    first_registration_date: date = Field(alias="firstRegistrationDate")
    images: list[str]
    image_urls: list[str] = Field(default_factory=list, alias="imageUrls")
    rebu: bool
    stock_id: str = Field(alias="_id")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def coerce_from_model(cls, data):
        if hasattr(data, "slug"):
            keys = list(data.images or [])
            return {
                "uuid": data.uuid,
                "uid": data.uid,
                "_id": f"stock-{data.slug}",
                "slug": data.slug,
                "title": data.title,
                "description": data.description,
                "brand": data.brand,
                "model": data.model,
                "year": data.year,
                "odometer": data.odometer,
                "price": data.price,
                "currency": data.currency,
                "saleStatus": data.sale_status,
                "motorType": data.motor_type,
                "driveType": data.drive_type,
                "fuelType": data.fuel_type,
                "firstRegistrationDate": data.first_registration_date,
                "images": keys,
                "imageUrls": public_urls_for_keys(keys),
                "rebu": data.rebu,
            }
        return data


class WebVehicleListResponse(BaseModel):
    vehicles: list[WebVehiclePublic]
