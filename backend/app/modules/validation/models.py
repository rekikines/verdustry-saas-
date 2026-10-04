from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    doc_type: Mapped[str] = mapped_column(String(80), default="Document")
    category: Mapped[str] = mapped_column(String(80), default="Achats")
    status: Mapped[str] = mapped_column(String(40), default="PENDING")
    # PENDING | VALIDATED | REJECTED
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # texte brut issu de l'OCR - necessaire pour le few-shot LLM et
    # l'entrainement du classificateur local (Fonctionnalite 5 : apprentissage progressif)
    source_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    site_id: Mapped[str] = mapped_column(String(40), ForeignKey("sites.id"))
    company_id: Mapped[str] = mapped_column(String(40), ForeignKey("companies.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
