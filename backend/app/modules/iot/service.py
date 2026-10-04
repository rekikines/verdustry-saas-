"""
Service métier — app/modules/iot/service.py

Toute fonction qui touche des données IoT reçoit `company_id` explicitement
(dérivé de l'utilisateur connecté côté router, jamais du payload client)
et filtre systématiquement dessus, conformément à la convention tenant du
projet.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy import select, func
from app.modules.sources.models import DataSource

from app.modules.iot.models import (
    IoTDevice, IoTGateway, IoTReading, IoTAlert,
    IoTDeviceStatus, IoTQualityFlag, IoTAlertType,
)
from app.modules.iot.schemas import DeviceCreate, DeviceUpdate, GatewayCreate, ReadingIn


# ---------------------------------------------------------------------------
# Gateways
# ---------------------------------------------------------------------------

def create_gateway(db: Session, company_id: str, payload: GatewayCreate) -> IoTGateway:
    gateway = IoTGateway(company_id=company_id, site_id=payload.site_id, name=payload.name)
    db.add(gateway)
    db.commit()
    db.refresh(gateway)
    return gateway


def list_gateways(db: Session, company_id: str, site_id: str | None = None) -> list[IoTGateway]:
    stmt = select(IoTGateway).where(IoTGateway.company_id == company_id)
    if site_id:
        stmt = stmt.where(IoTGateway.site_id == site_id)
    return list(db.scalars(stmt))


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------

def create_device(db: Session, company_id: str, payload: DeviceCreate) -> IoTDevice:
    device = IoTDevice(
        company_id=company_id,
        site_id=payload.site_id,
        gateway_id=payload.gateway_id,
        data_source_id=payload.data_source_id,
        device_uid=payload.device_uid,
        name=payload.name,
        device_type=payload.device_type,
        category=payload.category,
        protocol=payload.protocol,
        connection_params=payload.connection_params,
        unit=payload.unit,
        min_valid_value=payload.min_valid_value,
        max_valid_value=payload.max_valid_value,
        alert_threshold=payload.alert_threshold,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def list_devices(db: Session, company_id: str, site_id: str | None = None) -> list[IoTDevice]:
    stmt = select(IoTDevice).where(IoTDevice.company_id == company_id)
    if site_id:
        stmt = stmt.where(IoTDevice.site_id == site_id)
    return list(db.scalars(stmt))


def get_device(db: Session, company_id: str, device_id: str) -> IoTDevice | None:
    stmt = select(IoTDevice).where(IoTDevice.company_id == company_id, IoTDevice.id == device_id)
    return db.scalars(stmt).first()


def get_device_by_uid(db: Session, device_uid: str) -> IoTDevice | None:
    """Utilisé lors de l'ingestion : le device s'identifie par device_uid,
    pas par company_id (la gateway/capteur ne connaît pas le tenant)."""
    stmt = select(IoTDevice).where(IoTDevice.device_uid == device_uid)
    return db.scalars(stmt).first()


def update_device(db: Session, company_id: str, device_id: str, payload: DeviceUpdate) -> IoTDevice | None:
    device = get_device(db, company_id, device_id)
    if not device:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(device, field, value)
    db.commit()
    db.refresh(device)
    return device


# ---------------------------------------------------------------------------
# Ingestion des mesures
# ---------------------------------------------------------------------------

def ingest_reading(db: Session, payload: ReadingIn) -> IoTReading | None:
    """
    Point d'entrée unique pour toute donnée entrante (HTTP POST /iot/ingest
    ou message MQTT relayé par mqtt_client.py). Le device est retrouvé via
    device_uid : le company_id/site_id sont hérités du device en base, jamais
    fournis par la gateway (surface d'attaque sinon).
    """
    device = get_device_by_uid(db, payload.device_uid)
    if device is None:
        # Device inconnu : à journaliser (device non provisionné côté plateforme)
        return None

    ts = payload.timestamp or datetime.now(timezone.utc)
    quality_flag = _evaluate_quality(device, payload.value)

    reading = IoTReading(
        company_id=device.company_id,
        device_id=device.id,
        timestamp=ts,
        value=payload.value,
        raw_payload=payload.raw_payload,
        quality_flag=quality_flag,
    )
    db.add(reading)

    device.last_seen_at = ts
    if device.status == IoTDeviceStatus.error and quality_flag == IoTQualityFlag.ok:
        device.status = IoTDeviceStatus.active
    db.commit()
    db.refresh(reading)

    _sync_data_source_after_reading(db, device)   # ← ligne ajoutée
    _maybe_create_alerts(db, device, payload.value, quality_flag)

    return reading

def _evaluate_quality(device: IoTDevice, value: float) -> IoTQualityFlag:
    if device.min_valid_value is not None and value < device.min_valid_value:
        return IoTQualityFlag.out_of_range
    if device.max_valid_value is not None and value > device.max_valid_value:
        return IoTQualityFlag.out_of_range
    return IoTQualityFlag.ok


def _maybe_create_alerts(db: Session, device: IoTDevice, value: float, quality_flag: IoTQualityFlag) -> None:
    if quality_flag == IoTQualityFlag.out_of_range:
        db.add(IoTAlert(
            company_id=device.company_id,
            device_id=device.id,
            type=IoTAlertType.out_of_range,
            message=f"Valeur hors plage pour {device.name} : {value} {device.unit}",
        ))
    if device.alert_threshold is not None and value >= device.alert_threshold:
        db.add(IoTAlert(
            company_id=device.company_id,
            device_id=device.id,
            type=IoTAlertType.threshold_exceeded,
            message=f"Seuil dépassé pour {device.name} : {value} {device.unit} (seuil {device.alert_threshold})",
        ))
    db.commit()


# ---------------------------------------------------------------------------
# Lecture de l'historique
# ---------------------------------------------------------------------------

def list_readings(db: Session, company_id: str, device_id: str, start: datetime | None = None, end: datetime | None = None, limit: int = 500) -> list[IoTReading]:
    stmt = select(IoTReading).where(IoTReading.company_id == company_id, IoTReading.device_id == device_id)
    if start:
        stmt = stmt.where(IoTReading.timestamp >= start)
    if end:
        stmt = stmt.where(IoTReading.timestamp <= end)
    stmt = stmt.order_by(IoTReading.timestamp.desc()).limit(limit)
    return list(db.scalars(stmt))


def list_alerts(db: Session, company_id: str, device_id: str | None = None, unresolved_only: bool = True) -> list[IoTAlert]:
    stmt = select(IoTAlert).where(IoTAlert.company_id == company_id)
    if device_id:
        stmt = stmt.where(IoTAlert.device_id == device_id)
    if unresolved_only:
        stmt = stmt.where(IoTAlert.resolved_at.is_(None))
    return list(db.scalars(stmt))
def delete_device(db: Session, company_id: str, device_id: str) -> None:
    device = (
        db.query(IoTDevice)
        .filter(IoTDevice.id == device_id, IoTDevice.company_id == company_id)
        .first()
    )
    if not device:
        raise HTTPException(404, detail="Capteur introuvable.")

    # Supprime d'abord les mesures liées (contrainte de clé étrangère)
    db.query(IoTReading).filter(IoTReading.device_id == device.id).delete()
    db.delete(device)
    db.commit()

# ---------------------------------------------------------------------------
# Utilisé par le scheduler (détection devices hors ligne)
# ---------------------------------------------------------------------------

def flag_offline_devices(db: Session, offline_after_minutes: int = 30) -> list[IoTAlert]:
    from datetime import timedelta
    threshold = datetime.now(timezone.utc) - timedelta(minutes=offline_after_minutes)

    stmt = select(IoTDevice).where(
        IoTDevice.status == IoTDeviceStatus.active,
        (IoTDevice.last_seen_at.is_(None)) | (IoTDevice.last_seen_at < threshold),
    )
    stale_devices = list(db.scalars(stmt))
    new_alerts = []
    for device in stale_devices:
        device.status = IoTDeviceStatus.error
        alert = IoTAlert(
            company_id=device.company_id,
            device_id=device.id,
            type=IoTAlertType.offline,
            message=f"Aucune donnée reçue depuis plus de {offline_after_minutes} minutes pour {device.name}",
        )
        db.add(alert)
        new_alerts.append(alert)
    db.commit()
    return new_alerts
def _sync_data_source_after_reading(db: Session, device: IoTDevice) -> None:
    """Répercute chaque mesure IoT sur la DataSource liée (volume, last_sync_at,
    status), pour que la page Sources reflète l'activité réelle du capteur —
    équivalent du update fait par erp/service.py après un run_sync, mais
    déclenché par l'arrivée d'une mesure plutôt que par un clic Sync."""
    if not device.data_source_id:
        return
    source = db.query(DataSource).filter_by(id=device.data_source_id).first()
    if not source:
        return
    count = db.query(func.count(IoTReading.id)).filter(IoTReading.device_id == device.id).scalar()
    source.volume = f"{count} mesure(s)"
    source.last_sync_at = device.last_seen_at
    source.status = "ACTIVE"
    db.commit()