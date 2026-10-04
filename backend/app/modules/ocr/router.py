import shutil
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.models import Site, User
from app.modules.auth.router import get_current_user
from app.modules.ocr.service import is_ocr_available, engine_name, tesseract_available, process_document
from app.modules.sources.models import DataSource
from app.modules.validation.models import Extraction
from app.modules.validation.schemas import ExtractionOut
from app.modules.ocr.keyword_rules import keyword_classify
 
router = APIRouter(prefix="/api/ocr", tags=["OCR"])

UPLOAD_DIR = Path("uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}

# Fenetre anti-doublon : si le meme fichier (nom + site) a deja ete envoye
# il y a moins de X secondes, on ne relance pas d'appel LLM - on retourne
# le resultat existant. Evite les doubles appels API dus a un double-clic
# ou un re-render React, et economise du quota LLM au passage.
DEDUP_WINDOW_SECONDS = 30


@router.get("/status")
def ocr_status():
    return {
        "available": is_ocr_available(),
        "engine": engine_name(),
        "fallback": "tesseract" if tesseract_available() else None,
    }


@router.post("/extract", response_model=ExtractionOut)
async def extract_document(
    file: UploadFile = File(...),
    site_id: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

    site = (
        db.query(Site)
        .filter(Site.id == site_id, Site.company_id == user.company_id)
        .first()
    )
    if not site:
        raise HTTPException(400, detail="Site invalide.")

    original = file.filename or "document.bin"
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(400, detail=f"Format non supporté: {suffix}")

    # --- Verification anti-doublon ---
    # Meme nom de fichier, meme site, meme entreprise, cree tres recemment :
    # on considere que c'est une double soumission, pas un vrai nouveau document.
    cutoff = datetime.utcnow() - timedelta(seconds=DEDUP_WINDOW_SECONDS)
    recent_duplicate = (
        db.query(Extraction)
        .filter(
            Extraction.filename == original,
            Extraction.site_id == site_id,
            Extraction.company_id == user.company_id,
            Extraction.created_at >= cutoff,
        )
        .order_by(Extraction.created_at.desc())
        .first()
    )
    if recent_duplicate:
        return recent_duplicate

    safe = f"{uuid4().hex[:8]}_{Path(original).name}"
    dest = UPLOAD_DIR / safe
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    result = process_document(dest, db=db)
    mode = result["ocr_mode"]

    source = DataSource(
        id=f"ds-{uuid4().hex[:12]}",
        name=original,
        type="DOCUMENT",
        category=result["category"],
        status="ACTIVE" if mode == "tesseract" else "OCR_PENDING",
        volume="1 doc",
        config={
            "file": safe,
            "ocr_mode": mode,
            "doc_type": result["doc_type"],
        },
        site_id=site_id,
        company_id=user.company_id,
    )
    db.add(source)

    extraction = Extraction(
        id=f"ext-{uuid4().hex[:12]}",
        filename=original,
        doc_type=result["doc_type"],
        category=result["category"],
        status="PENDING",
        confidence=result["confidence"],
        fields={
            **result["fields"],
            "_ocr_mode": mode,
            "_extraction_source": result.get("extraction_source", "rules"),
        },
        raw_text=result["raw_text"],
        source_id=source.id,
        site_id=site_id,
        company_id=user.company_id,
    )
    db.add(extraction)
    db.commit()
    db.refresh(extraction)
    return extraction
