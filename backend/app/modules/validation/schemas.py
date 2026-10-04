from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ExtractionCreate(BaseModel):
    filename: str
    doc_type: str = "Document"
    category: str = "Achats"
    confidence: float = 0.8
    fields: dict[str, Any] = Field(default_factory=dict)
    source_id: str | None = None
    site_id: str


class ExtractionOut(BaseModel):
    id: str
    filename: str
    doc_type: str
    category: str
    status: str
    confidence: float
    fields: dict[str, Any] | None = None
    source_id: str | None = None
    site_id: str
    company_id: str
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ExtractionUpdateFields(BaseModel):
    fields: dict[str, Any]