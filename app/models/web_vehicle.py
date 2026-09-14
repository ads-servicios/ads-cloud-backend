from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VehicleCurrency(StrEnum):
    EUR = "EUR"
    DOL = "DOL"


class VehicleSaleStatus(StrEnum):
    SOLD = "sold"
    AVAILABLE = "available"


class VehicleDriveType(StrEnum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class VehicleFuelType(StrEnum):
    DIESEL = "diesel"
    GASOLIN = "gasolin"
    ELECTRIC = "electric"


class WebVehicle(Base):
    __tablename__ = "web_vehicles"

    uid: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    odometer: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    sale_status: Mapped[str] = mapped_column(String(32), nullable=False)
    motor_type: Mapped[str] = mapped_column(String(120), nullable=False)
    drive_type: Mapped[str] = mapped_column(String(32), nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(32), nullable=False)
    first_registration_date: Mapped[date] = mapped_column(Date, nullable=False)
    images: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rebu: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
