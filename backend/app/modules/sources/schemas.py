from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., pattern="^(DOCUMENT|ERP|API|IOT|CSV|SQL|MANUAL)$")
    category: str = Field(default="Achats", max_length=80)
    site_id: str
    config: dict[str, Any] = Field(default_factory=dict)


class SourceOut(BaseModel):
    id: str
    name: str
    type: str
    category: str
    status: str
    volume: str | None = None
    site_id: str
    company_id: str
    last_sync_at: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


CONNECTION_TYPES = [
    {"type": "DOCUMENT", "label": "Document (PDF / Image)", "primary": True,
     "description": "Factures — extraction OCR automatique"},
    {"type": "ERP", "label": "ERP", "primary": False, "description": "Odoo, SAP…"},
    {"type": "API", "label": "API externe", "primary": False, "description": "REST / OAuth"},
    {"type": "IOT", "label": "IoT / Compteur", "primary": False, "description": "STEG, SONEDE…"},
    {"type": "CSV", "label": "Fichier CSV / Excel", "primary": False,
     "description": "Import .csv, .xlsx, .xls"},
    {"type": "SQL", "label": "Base SQL", "primary": False, "description": "Lecture seule"},
    {"type": "MANUAL", "label": "Saisie manuelle", "primary": False, "description": "Formulaire"},
]