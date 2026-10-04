import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Enum, Integer, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ERPType(str, enum.Enum):
    odoo = "odoo"
    sap = "sap"
    sage = "sage"
    oracle = "oracle"


class ERPSyncStatus(str, enum.Enum):
    pending = "pending"
    connected = "connected"
    error = "error"
    syncing = "syncing"


class ERPConnection(Base):
    __tablename__ = "erp_connections"

    id = Column(String, primary_key=True, default=lambda: f"erp-{uuid4().hex[:10]}")
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    site_id = Column(String, ForeignKey("sites.id"), nullable=True)

    name = Column(String, nullable=False)
    erp_type = Column(Enum(ERPType), default=ERPType.odoo, nullable=False)

    url = Column(String, nullable=False)
    db_name = Column(String, nullable=False)
    username = Column(String, nullable=False)
    credentials_encrypted = Column(Text, nullable=False)

    status = Column(Enum(ERPSyncStatus), default=ERPSyncStatus.pending, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    sync_frequency = Column(String, default="daily")  # realtime | hourly | daily | manual
    scope_config = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    field_mappings = relationship("ERPFieldMapping", back_populates="connection", cascade="all, delete-orphan")
    sync_logs = relationship("ERPSyncLog", back_populates="connection", cascade="all, delete-orphan")


class ERPFieldMapping(Base):
    __tablename__ = "erp_field_mappings"

    id = Column(String, primary_key=True, default=lambda: f"map-{uuid4().hex[:10]}")
    connection_id = Column(String, ForeignKey("erp_connections.id"), nullable=False)

    odoo_model = Column(String, nullable=False)
    source_field = Column(String, nullable=False)
    target_field = Column(String, nullable=False)
    transform = Column(String, nullable=True)
    is_auto_learned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    connection = relationship("ERPConnection", back_populates="field_mappings")


class ERPSyncLog(Base):
    __tablename__ = "erp_sync_logs"

    id = Column(String, primary_key=True, default=lambda: f"log-{uuid4().hex[:10]}")
    connection_id = Column(String, ForeignKey("erp_connections.id"), nullable=False)

    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="running")
    records_extracted = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    connection = relationship("ERPConnection", back_populates="sync_logs")