from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User

from . import service
from .models import APIConnection
from .schemas import APIConnectionCreate, APIConnectionOut, APITestConnectionResult, APISyncTriggerResult

router = APIRouter(prefix="/api/external-api", tags=["API externe"])


def _get_connection_or_404(db, connection_id, company_id):
    conn = db.query(APIConnection).filter_by(id=connection_id, company_id=company_id).first()
    if not conn:
        raise HTTPException(404, detail="Connexion API introuvable")
    return conn

@router.delete("/devices/{device_id}")
def delete_device(
    device_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service.delete_device(db, company_id=user.company_id, device_id=device_id)
    return {"ok": True, "id": device_id}
@router.post("/connections", response_model=APIConnectionOut, status_code=201)
def create_api_connection(payload: APIConnectionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("ADMIN", "RESPONSABLE_ENV"):
        raise HTTPException(403, detail="Droits insuffisants.")
    return service.create_connection(db, user.company_id, payload)


@router.post("/connections/{connection_id}/test", response_model=APITestConnectionResult)
def test_api_connection(connection_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = _get_connection_or_404(db, connection_id, user.company_id)
    ok, message = service.test_connection(db, conn)
    return APITestConnectionResult(success=ok, message=message)


@router.post("/connections/{connection_id}/sync", response_model=APISyncTriggerResult)
def trigger_api_sync(connection_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = _get_connection_or_404(db, connection_id, user.company_id)
    log = service.run_sync(db, conn)
    return APISyncTriggerResult(sync_log_id=log.id, status=log.status, records_extracted=log.records_extracted)