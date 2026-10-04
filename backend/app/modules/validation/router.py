from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.models import Site, User
from app.modules.auth.router import get_current_user
from app.modules.validation.models import Extraction
from app.modules.validation.schemas import (
    ExtractionCreate,
    ExtractionOut,
    ExtractionUpdateFields,
)

router = APIRouter(prefix="/api/validation", tags=["Validation"])


@router.get("", response_model=list[ExtractionOut])
def list_extractions(
    status: str | None = Query("PENDING"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Extraction).filter(Extraction.company_id == user.company_id)
    if status:
        q = q.filter(Extraction.status == status)
    return q.order_by(Extraction.created_at.desc()).all()


@router.post("", response_model=ExtractionOut, status_code=201)
def create_extraction(
    body: ExtractionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    site = (
        db.query(Site)
        .filter(Site.id == body.site_id, Site.company_id == user.company_id)
        .first()
    )
    if not site:
        raise HTTPException(400, detail="Site invalide.")

    row = Extraction(
        id=f"ext-{uuid4().hex[:12]}",
        filename=body.filename.strip(),
        doc_type=body.doc_type,
        category=body.category,
        status="PENDING",
        confidence=body.confidence,
        fields=body.fields or {},
        source_id=body.source_id,
        site_id=body.site_id,
        company_id=user.company_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/{extraction_id}/validate", response_model=ExtractionOut)
def validate(
    extraction_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = (
        db.query(Extraction)
        .filter(
            Extraction.id == extraction_id,
            Extraction.company_id == user.company_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(404, detail="Extraction introuvable.")
    row.status = "VALIDATED"
    db.commit()
    db.refresh(row)
    return row


@router.post("/{extraction_id}/reject", response_model=ExtractionOut)
def reject(
    extraction_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = (
        db.query(Extraction)
        .filter(
            Extraction.id == extraction_id,
            Extraction.company_id == user.company_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(404, detail="Extraction introuvable.")
    row.status = "REJECTED"
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{extraction_id}/fields", response_model=ExtractionOut)
def update_fields(
    extraction_id: str,
    body: ExtractionUpdateFields,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = (
        db.query(Extraction)
        .filter(
            Extraction.id == extraction_id,
            Extraction.company_id == user.company_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(404, detail="Extraction introuvable.")
    row.fields = body.fields
    db.commit()
    db.refresh(row)
    return row


@router.post("/seed-demo", response_model=list[ExtractionOut])
def seed_demo(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Crée 2 extractions de démo pour tester l'UI."""
    site_id = user.site_id
    if not site_id:
        site = db.query(Site).filter(Site.company_id == user.company_id).first()
        if not site:
            raise HTTPException(400, detail="Aucun site. Créez un site d'abord.")
        site_id = site.id

    demos = [
        {
            "filename": "facture_steg_juillet.pdf",
            "doc_type": "Facture énergie",
            "category": "Énergie",
            "confidence": 0.91,
            "fields": {
                "Fournisseur": "STEG",
                "Montant TTC": "92.000 TND",
                "Référence": "93797 480 0",
                "Période": "06/10/2022 – 09/08/2022",
            },
        },
        {
            "filename": "bordereau_dechets_s24.pdf",
            "doc_type": "Bordereau",
            "category": "Déchets",
            "confidence": 0.84,
            "fields": {
                "Quantité": "2,4 t",
                "Type": "Déchets industriels",
                "Date": "24/07/2026",
            },
        },
    ]
    created = []
    for d in demos:
        row = Extraction(
            id=f"ext-{uuid4().hex[:12]}",
            filename=d["filename"],
            doc_type=d["doc_type"],
            category=d["category"],
            status="PENDING",
            confidence=d["confidence"],
            fields=d["fields"],
            site_id=site_id,
            company_id=user.company_id,
        )
        db.add(row)
        created.append(row)
    db.commit()
    for r in created:
        db.refresh(r)
    return created