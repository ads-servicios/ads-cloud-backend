from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.web_vehicle import WebVehicle
from app.schemas.web_vehicles import WebVehicleCreate, WebVehicleUpdate
from app.services.web_vehicle_media import ImageUpload, WebVehicleMediaError, resolve_images_for_vehicle


class WebVehicleNotFoundError(Exception):
    pass


class WebVehicleConflictError(Exception):
    pass


async def list_web_vehicles(db: AsyncSession) -> list[WebVehicle]:
    result = await db.execute(select(WebVehicle).order_by(WebVehicle.uid))
    return list(result.scalars().all())


async def get_web_vehicle(db: AsyncSession, vehicle_uuid: str) -> WebVehicle:
    result = await db.execute(select(WebVehicle).where(WebVehicle.uuid == vehicle_uuid))
    vehicle = result.scalar_one_or_none()
    if vehicle is None:
        raise WebVehicleNotFoundError(f"Web vehicle {vehicle_uuid} not found")
    return vehicle


def _scalar_fields(payload: WebVehicleCreate | WebVehicleUpdate) -> dict:
    data = payload.model_dump(exclude_unset=True, by_alias=False)
    data.pop("images", None)
    return data


def _apply_scalars(vehicle: WebVehicle, payload: WebVehicleCreate | WebVehicleUpdate) -> None:
    for field, value in _scalar_fields(payload).items():
        setattr(vehicle, field, value)


async def create_web_vehicle(db: AsyncSession, payload: WebVehicleCreate) -> WebVehicle:
    vehicle = WebVehicle(uuid=str(uuid4()), images=[])
    _apply_scalars(vehicle, payload)
    db.add(vehicle)
    try:
        await db.flush()
        vehicle.images = resolve_images_for_vehicle(vehicle.uid, list(payload.images))
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise WebVehicleConflictError("Slug already registered") from exc
    except WebVehicleMediaError:
        await db.rollback()
        raise
    return await get_web_vehicle(db, vehicle.uuid)


async def replace_web_vehicle(
    db: AsyncSession,
    vehicle_uuid: str,
    payload: WebVehicleCreate,
) -> WebVehicle:
    vehicle = await get_web_vehicle(db, vehicle_uuid)
    _apply_scalars(vehicle, payload)
    try:
        vehicle.images = resolve_images_for_vehicle(vehicle.uid, list(payload.images))
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise WebVehicleConflictError("Slug already registered") from exc
    except WebVehicleMediaError:
        await db.rollback()
        raise
    return await get_web_vehicle(db, vehicle.uuid)


async def update_web_vehicle(
    db: AsyncSession,
    vehicle_uuid: str,
    payload: WebVehicleUpdate,
) -> WebVehicle:
    vehicle = await get_web_vehicle(db, vehicle_uuid)
    _apply_scalars(vehicle, payload)
    try:
        if "images" in payload.model_fields_set:
            vehicle.images = resolve_images_for_vehicle(
                vehicle.uid,
                list(payload.images or []),
            )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise WebVehicleConflictError("Slug already registered") from exc
    except WebVehicleMediaError:
        await db.rollback()
        raise
    return await get_web_vehicle(db, vehicle.uuid)


async def delete_web_vehicle(db: AsyncSession, vehicle_uuid: str) -> None:
    vehicle = await get_web_vehicle(db, vehicle_uuid)
    await db.delete(vehicle)
    await db.commit()
