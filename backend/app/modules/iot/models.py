"""
Modèles SQLAlchemy du module IoT — app/modules/iot/models.py

Conventions appliquées :
- Tables en snake_case pluriel
- PK String préfixée : iot- (device), gw- (gateway), rd- (reading), al- (alert)
- company_id sur CHAQUE table (tenant) + site_id (sous-organisation)
- Filtrage tenant systématique à faire dans service.py via l'utilisateur connecté
  (jamais uniquement côté route — voir service.py)
"""

from datetime import datetime
import enum

from sqlalchemy import String, ForeignKey, DateTime, Float, Enum, func, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import generate_id


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class IoTProtocol(str, enum.Enum):
    modbus_rtu = "modbus_rtu"
    modbus_tcp = "modbus_tcp"
    mqtt = "mqtt"
    lorawan = "lorawan"
    http = "http"
    simulator = "simulator"


class IoTCategory(str, enum.Enum):
    energie = "energie"
    eau = "eau"
    dechets = "dechets"
    emissions = "emissions"
    ambiance = "ambiance"


class IoTDeviceStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    error = "error"


class IoTGatewayStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    degraded = "degraded"


class IoTQualityFlag(str, enum.Enum):
    ok = "ok"
    out_of_range = "out_of_range"
    duplicate = "duplicate"
    gap_filled = "gap_filled"


class IoTAlertType(str, enum.Enum):
    offline = "offline"
    out_of_range = "out_of_range"
    threshold_exceeded = "threshold_exceeded"


# ---------------------------------------------------------------------------
# iot_gateways
# ---------------------------------------------------------------------------

class IoTGateway(Base):
    __tablename__ = "iot_gateways"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: generate_id("gw"))
    company_id: Mapped[str] = mapped_column(String(40), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id: Mapped[str] = mapped_column(String(40), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[IoTGatewayStatus] = mapped_column(Enum(IoTGatewayStatus, name="iot_gateway_status"), default=IoTGatewayStatus.offline, nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    devices: Mapped[list["IoTDevice"]] = relationship(back_populates="gateway")

    __table_args__ = (
        Index("ix_iot_gateways_company_site", "company_id", "site_id"),
    )


# ---------------------------------------------------------------------------
# iot_devices
# ---------------------------------------------------------------------------

class IoTDevice(Base):
    __tablename__ = "iot_devices"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: generate_id("iot"))
    company_id: Mapped[str] = mapped_column(String(40), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id: Mapped[str] = mapped_column(String(40), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)

    data_source_id: Mapped[str | None] = mapped_column(String(40), ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    gateway_id: Mapped[str | None] = mapped_column(String(40), ForeignKey("iot_gateways.id", ondelete="SET NULL"), nullable=True, index=True)

    device_uid: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    device_type: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[IoTCategory] = mapped_column(Enum(IoTCategory, name="iot_category"), nullable=False)
    protocol: Mapped[IoTProtocol] = mapped_column(Enum(IoTProtocol, name="iot_protocol"), nullable=False)

    connection_params: Mapped[dict] = mapped_column(JSONB, default=dict)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    min_valid_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_valid_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    alert_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[IoTDeviceStatus] = mapped_column(Enum(IoTDeviceStatus, name="iot_device_status"), default=IoTDeviceStatus.active, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    gateway: Mapped["IoTGateway | None"] = relationship(back_populates="devices")
    readings: Mapped[list["IoTReading"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    alerts: Mapped[list["IoTAlert"]] = relationship(back_populates="device", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_iot_devices_company_site", "company_id", "site_id"),
    )


# ---------------------------------------------------------------------------
# iot_readings
# ---------------------------------------------------------------------------

class IoTReading(Base):
    __tablename__ = "iot_readings"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: generate_id("rd"))
    company_id: Mapped[str] = mapped_column(String(40), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(40), ForeignKey("iot_devices.id", ondelete="CASCADE"), nullable=False, index=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    quality_flag: Mapped[IoTQualityFlag] = mapped_column(Enum(IoTQualityFlag, name="iot_quality_flag"), default=IoTQualityFlag.ok, nullable=False)

    device: Mapped["IoTDevice"] = relationship(back_populates="readings")

    __table_args__ = (
        Index("ix_iot_readings_device_timestamp", "device_id", "timestamp"),
    )
    # NB: si TimescaleDB est activé -> SELECT create_hypertable('iot_readings', 'timestamp');


# ---------------------------------------------------------------------------
# iot_alerts
# ---------------------------------------------------------------------------

class IoTAlert(Base):
    __tablename__ = "iot_alerts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: generate_id("al"))
    company_id: Mapped[str] = mapped_column(String(40), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(40), ForeignKey("iot_devices.id", ondelete="CASCADE"), nullable=False, index=True)

    type: Mapped[IoTAlertType] = mapped_column(Enum(IoTAlertType, name="iot_alert_type"), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped["IoTDevice"] = relationship(back_populates="alerts")
