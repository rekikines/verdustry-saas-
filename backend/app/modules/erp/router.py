from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from .scheduler import unschedule_connection

from . import service
from .models import ERPConnection
from .schemas import (
    ERPConnectionCreate, ERPConnectionUpdate, ERPConnectionOut,
    ERPTestConnectionResult, ERPSyncTriggerResult,
)


router = APIRouter(prefix="/api/erp", tags=["ERP"])


def _get_connection_or_404(db: Session, connection_id: str, company_id: str) -> ERPConnection:
    conn = db.query(ERPConnection).filter_by(id=connection_id, company_id=company_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connexion ERP introuvable")
    return conn


@router.post("/connections", response_model=ERPConnectionOut, status_code=201)
def create_erp_connection(
    payload: ERPConnectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("ADMIN", "RESPONSABLE_ENV"):
        raise HTTPException(403, detail="Droits insuffisants pour connecter un ERP.")
    return service.create_connection(db, user.company_id, payload)


@router.get("/connections", response_model=list[ERPConnectionOut])
def list_erp_connections(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(ERPConnection).filter_by(company_id=user.company_id).all()


@router.post("/connections/{connection_id}/test", response_model=ERPTestConnectionResult)
def test_erp_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conn = _get_connection_or_404(db, connection_id, user.company_id)
    ok, message = service.test_connection(db, conn)
    return ERPTestConnectionResult(success=ok, message=message)


@router.post("/connections/{connection_id}/sync", response_model=ERPSyncTriggerResult)
def trigger_erp_sync(
    connection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conn = _get_connection_or_404(db, connection_id, user.company_id)
    log = service.run_sync(db, conn)
    return ERPSyncTriggerResult(
        sync_log_id=log.id, status=log.status, records_extracted=log.records_extracted
    )


@router.get("/connections/{connection_id}/logs")
def get_sync_logs(
    connection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conn = _get_connection_or_404(db, connection_id, user.company_id)
    return conn.sync_logs


@router.delete("/connections/{connection_id}")
def delete_erp_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "ADMIN":
        raise HTTPException(403, detail="Seul un ADMIN peut supprimer une connexion ERP.")
    conn = _get_connection_or_404(db, connection_id, user.company_id)
    unschedule_connection(conn.id) 
    db.delete(conn)
    db.commit()
    return {"ok": True, "id": connection_id}



@router.patch("/connections/{connection_id}", response_model=ERPConnectionOut)
def update_erp_connection(
    connection_id: str,
    payload: ERPConnectionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("ADMIN", "RESPONSABLE_ENV"):
        raise HTTPException(403, detail="Droits insuffisants pour modifier une connexion ERP.")
    conn = _get_connection_or_404(db, connection_id, user.company_id)

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(conn, field, value)

    db.commit()
    db.refresh(conn)

    if "sync_frequency" in data:
        from .scheduler import schedule_connection
        schedule_connection(conn.id, conn.sync_frequency)

    return conn