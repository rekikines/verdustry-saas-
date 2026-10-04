"""
Router FastAPI — app/modules/iot/router.py

Hypothèses sur vos dépendances existantes (adaptez les imports à vos noms
réels si différents) :
- get_db()              -> session SQLAlchemy (comme dans erp/router.py)
- get_current_user()    -> utilisateur authentifié (JWT), avec .company_id
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.router import get_current_user
from app.modules.iot import service
from app.modules.iot.schemas import (
    GatewayCreate, GatewayOut,
    DeviceCreate, DeviceUpdate, DeviceOut,
    ReadingIn, ReadingOut,
    AlertOut,
)

router = APIRouter(prefix="/api/iot", tags=["iot"])

# ---------------------------------------------------------------------------
# Gateways
# ---------------------------------------------------------------------------

@router.post("/gateways", response_model=GatewayOut, status_code=status.HTTP_201_CREATED)
def create_gateway(payload: GatewayCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return service.create_gateway(db, company_id=user.company_id, payload=payload)


@router.get("/gateways", response_model=list[GatewayOut])
def list_gateways(site_id: str | None = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return service.list_gateways(db, company_id=user.company_id, site_id=site_id)


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------

@router.post("/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return service.create_device(db, company_id=user.company_id, payload=payload)


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(site_id: str | None = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return service.list_devices(db, company_id=user.company_id, site_id=site_id)


@router.get("/devices/{device_id}", response_model=DeviceOut)
def get_device(device_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    device = service.get_device(db, company_id=user.company_id, device_id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    return device


@router.patch("/devices/{device_id}", response_model=DeviceOut)
def update_device(device_id: str, payload: DeviceUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    device = service.update_device(db, company_id=user.company_id, device_id=device_id, payload=payload)
    if not device:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    return device


@router.get("/devices/{device_id}/readings", response_model=list[ReadingOut])
def get_device_readings(
    device_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 500,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    device = service.get_device(db, company_id=user.company_id, device_id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Capteur introuvable")
    return service.list_readings(db, company_id=user.company_id, device_id=device_id, start=start, end=end, limit=limit)


# ---------------------------------------------------------------------------
# Ingestion — endpoint appelé par la gateway physique (pas par le frontend)
# ---------------------------------------------------------------------------
#
# NB sécurité : cet endpoint n'est PAS protégé par get_current_user (la
# gateway n'a pas de session utilisateur). Il doit être protégé par une
# clé d'API dédiée par gateway/device (voir security_vault.py) avant mise
# en production. Pour le test avec un simulateur en ligne, un secret
# partagé simple (header X-Device-Key) suffit dans un premier temps.

@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest_reading(payload: ReadingIn, db: Session = Depends(get_db)):
    reading = service.ingest_reading(db, payload)
    if reading is None:
        raise HTTPException(status_code=404, detail="device_uid inconnu — capteur non provisionné sur la plateforme")
    return {"status": "accepted", "reading_id": reading.id}


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(device_id: str | None = None, unresolved_only: bool = True, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return service.list_alerts(db, company_id=user.company_id, device_id=device_id, unresolved_only=unresolved_only)
