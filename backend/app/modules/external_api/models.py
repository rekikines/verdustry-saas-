import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Enum, Integer, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuthType(str, enum.Enum):
    none = "none"
    api_key = "api_key"      # clé envoyée dans un header
    bearer = "bearer"        # Authorization: Bearer <token>
    basic = "basic"          # Basic Auth user/password


class APISyncStatus(str, enum.Enum):
    pending = "pending"
    connected = "connected"
    error = "error"
    syncing = "syncing"


class APIConnection(Base):
    __tablename__ = "api_connections"

    id = Column(String, primary_key=True, default=lambda: f"api-{uuid4().hex[:10]}")
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    site_id = Column(String, ForeignKey("sites.id"), nullable=True)

    name = Column(String, nullable=False)
    category = Column(String, nullable=False, default="Achats")

    base_url = Column(String, nullable=False)
    endpoint_path = Column(String, nullable=False, default="")
    http_method = Column(String, nullable=False, default="GET")
    query_params = Column(JSON, default=dict)
    request_body = Column(JSON, nullable=True)

    auth_type = Column(Enum(AuthType), default=AuthType.none, nullable=False)
    credentials_encrypted = Column(Text, nullable=True)

    # Chemin vers le tableau d'enregistrements dans la reponse JSON, ex: "data.items"
    response_data_path = Column(String, nullable=False, default="")

    pagination_type = Column(String, default="none")  # none | page | offset | cursor
    pagination_config = Column(JSON, default=dict)

    field_map = Column(JSON, default=dict)  # {"champ.imbrique": "Champ cible"}

    status = Column(Enum(APISyncStatus), default=APISyncStatus.pending, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    sync_frequency = Column(String, default="daily")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sync_logs = relationship("APISyncLog", back_populates="connection", cascade="all, delete-orphan")


class APISyncLog(Base):
    __tablename__ = "api_sync_logs"

    id = Column(String, primary_key=True, default=lambda: f"log-{uuid4().hex[:10]}")
    connection_id = Column(String, ForeignKey("api_connections.id"), nullable=False)

    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="running")
    records_extracted = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    connection = relationship("APIConnection", back_populates="sync_logs")