from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Action, require_permission
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.web_vehicles import WebVehicleCreate, WebVehicleListResponse, WebVehiclePublic, WebVehicleUpdate
from app.services import web_vehicles as web_vehicles_service
from app.services.web_vehicle_media import WebVehicleMediaError

router = APIRouter(prefix="/web_vehicles", tags=["web_vehicles"])


@router.get("", response_model=WebVehicleListResponse)
async def list_web_vehicles(
    db: AsyncSession = Depends(get_db_session),
) -> WebVehicleListResponse:
    return WebVehicleListResponse(vehicles=await web_vehicles_service.list_web_vehicles(db))


@router.get("/{vehicle_uuid}", response_model=WebVehiclePublic)
async def get_web_vehicle(
    vehicle_uuid: str,
    db: AsyncSession = Depends(get_db_session),
) -> WebVehiclePublic:
    try:
        return await web_vehicles_service.get_web_vehicle(db, vehicle_uuid)
    except web_vehicles_service.WebVehicleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Web vehicle not found") from None


@router.post("", response_model=WebVehiclePublic, status_code=status.HTTP_201_CREATED)
async def create_web_vehicle(
    payload: WebVehicleCreate,
    _: User = Depends(require_permission("web_vehicles", Action.CREATE)),
    db: AsyncSession = Depends(get_db_session),
) -> WebVehiclePublic:
    try:
        return await web_vehicles_service.create_web_vehicle(db, payload)
    except web_vehicles_service.WebVehicleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except WebVehicleMediaError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None


@router.put("/{vehicle_uuid}", response_model=WebVehiclePublic)
async def replace_web_vehicle(
    vehicle_uuid: str,
    payload: WebVehicleCreate,
    _: User = Depends(require_permission("web_vehicles", Action.EDIT)),
    db: AsyncSession = Depends(get_db_session),
) -> WebVehiclePublic:
    try:
        return await web_vehicles_service.replace_web_vehicle(db, vehicle_uuid, payload)
    except web_vehicles_service.WebVehicleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Web vehicle not found") from None
    except web_vehicles_service.WebVehicleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except WebVehicleMediaError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None


@router.patch("/{vehicle_uuid}", response_model=WebVehiclePublic)
async def patch_web_vehicle(
    vehicle_uuid: str,
    payload: WebVehicleUpdate,
    _: User = Depends(require_permission("web_vehicles", Action.EDIT)),
    db: AsyncSession = Depends(get_db_session),
) -> WebVehiclePublic:
    try:
        return await web_vehicles_service.update_web_vehicle(db, vehicle_uuid, payload)
    except web_vehicles_service.WebVehicleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Web vehicle not found") from None
    except web_vehicles_service.WebVehicleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except WebVehicleMediaError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None


@router.delete("/{vehicle_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_web_vehicle(
    vehicle_uuid: str,
    _: User = Depends(require_permission("web_vehicles", Action.DELETE)),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await web_vehicles_service.delete_web_vehicle(db, vehicle_uuid)
    except web_vehicles_service.WebVehicleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Web vehicle not found") from None
