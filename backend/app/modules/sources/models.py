from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(40))
    # DOCUMENT | ERP | API | IOT | CSV | SQL | MANUAL
    category: Mapped[str] = mapped_column(String(80), default="Achats")
    status: Mapped[str] = mapped_column(String(40), default="INACTIVE")
    # ACTIVE | FAILED | OCR_PENDING | INACTIVE
    volume: Mapped[str | None] = mapped_column(String(40), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    site_id: Mapped[str] = mapped_column(String(40), ForeignKey("sites.id"))
    company_id: Mapped[str] = mapped_column(String(40), ForeignKey("companies.id"))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)