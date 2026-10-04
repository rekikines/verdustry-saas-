from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.router import get_current_user
from app.modules.sources import service
from app.modules.sources.schemas import CONNECTION_TYPES, SourceCreate, SourceOut

router = APIRouter(prefix="/api/sources", tags=["Sources"])


@router.get("/connection-types")
def connection_types():
    return CONNECTION_TYPES


@router.get("", response_model=list[SourceOut])
def list_sources(
    site_id: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.list_sources(db, user, site_id)


@router.post("", response_model=SourceOut, status_code=201)
def create_source(
    body: SourceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.create_source(
        db,
        user,
        name=body.name,
        type_=body.type,
        category=body.category,
        site_id=body.site_id,
        config=body.config,
    )


@router.post("/{source_id}/sync", response_model=SourceOut)
def sync_source(
    source_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.sync_source(db, user, source_id)


@router.delete("/{source_id}")
def delete_source(
    source_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service.delete_source(db, user, source_id)
    return {"ok": True, "id": source_id}