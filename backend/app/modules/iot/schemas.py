"""
Schémas Pydantic — app/modules/iot/schemas.py
"""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.modules.iot.models import (
    IoTProtocol, IoTCategory, IoTDeviceStatus, IoTGatewayStatus,
    IoTQualityFlag, IoTAlertType,
)


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------

class GatewayCreate(BaseModel):
    site_id: str
    name: str


class GatewayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    name: str
    status: IoTGatewayStatus
    last_heartbeat_at: datetime | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------

class DeviceCreate(BaseModel):
    site_id: str
    gateway_id: str | None = None
    data_source_id: str | None = None

    device_uid: str = Field(..., description="Identifiant matériel unique (n° série, DevEUI, client_id MQTT)")
    name: str
    device_type: str = Field(..., description="ex: energy_meter, water_flow, co2, pm25, waste_level, weight")
    category: IoTCategory
    protocol: IoTProtocol
    connection_params: dict = Field(default_factory=dict)
    unit: str

    min_valid_value: float | None = None
    max_valid_value: float | None = None
    alert_threshold: float | None = None


class DeviceUpdate(BaseModel):
    name: str | None = None
    status: IoTDeviceStatus | None = None
    connection_params: dict | None = None
    min_valid_value: float | None = None
    max_valid_value: float | None = None
    alert_threshold: float | None = None


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    gateway_id: str | None
    data_source_id: str | None
    device_uid: str
    name: str
    device_type: str
    category: IoTCategory
    protocol: IoTProtocol
    unit: str
    status: IoTDeviceStatus
    last_seen_at: datetime | None
    min_valid_value: float | None
    max_valid_value: float | None
    alert_threshold: float | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Reading (ingestion + lecture)
# ---------------------------------------------------------------------------

class ReadingIn(BaseModel):
    """Payload attendu depuis une gateway (HTTP POST /iot/ingest ou message MQTT)."""

    device_uid: str = Field(..., description="Identifiant matériel du capteur émetteur")
    timestamp: datetime | None = Field(None, description="Horodatage de la mesure ; si absent, l'heure de réception est utilisée")
    value: float
    raw_payload: str | dict | None = None

class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    device_id: str
    timestamp: datetime
    value: float
    quality_flag: IoTQualityFlag


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------

class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    device_id: str
    type: IoTAlertType
    message: str
    created_at: datetime
    resolved_at: datetime | None
