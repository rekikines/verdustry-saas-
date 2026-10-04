from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.models import Site, User
from app.modules.auth.router import get_current_user
from app.modules.sites.schemas import SiteCreate, SiteUpdate, SiteOut

router = APIRouter(prefix="/api/sites", tags=["Sites"])


@router.get("", response_model=list[SiteOut])
def list_sites(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sites de la société de l'utilisateur uniquement."""
    rows = (
        db.query(Site)
        .filter(Site.company_id == user.company_id)
        .order_by(Site.name)
        .all()
    )
    return rows


@router.post("", response_model=SiteOut, status_code=201)
def create_site(
    body: SiteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("ADMIN", "RESPONSABLE_ENV"):
        raise HTTPException(403, detail="Droits insuffisants pour créer un site.")

    site = Site(
        id=f"site-{uuid4().hex[:10]}",
        name=body.name.strip(),
        location=(body.location or "").strip() or None,
        company_id=user.company_id,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


@router.get("/{site_id}", response_model=SiteOut)
def get_site(
    site_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    site = (
        db.query(Site)
        .filter(Site.id == site_id, Site.company_id == user.company_id)
        .first()
    )
    if not site:
        raise HTTPException(404, detail="Site introuvable.")
    return site


@router.patch("/{site_id}", response_model=SiteOut)
def update_site(
    site_id: str,
    body: SiteUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("ADMIN", "RESPONSABLE_ENV"):
        raise HTTPException(403, detail="Droits insuffisants.")

    site = (
        db.query(Site)
        .filter(Site.id == site_id, Site.company_id == user.company_id)
        .first()
    )
    if not site:
        raise HTTPException(404, detail="Site introuvable.")

    if body.name is not None:
        site.name = body.name.strip()
    if body.location is not None:
        site.location = body.location.strip() or None

    db.commit()
    db.refresh(site)
    return site


@router.delete("/{site_id}")
def delete_site(
    site_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "ADMIN":
        raise HTTPException(403, detail="Seul un ADMIN peut supprimer un site.")

    site = (
        db.query(Site)
        .filter(Site.id == site_id, Site.company_id == user.company_id)
        .first()
    )
    if not site:
        raise HTTPException(404, detail="Site introuvable.")

    db.delete(site)
    db.commit()
    return {"ok": True, "id": site_id}