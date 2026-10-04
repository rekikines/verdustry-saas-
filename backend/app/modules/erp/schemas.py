from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from .models import ERPType, ERPSyncStatus


class ERPConnectionCreate(BaseModel):
    name: str
    erp_type: ERPType = ERPType.odoo
    site_id: Optional[str] = None
    url: str
    db_name: str
    username: str
    password: str
    sync_frequency: str = "daily"
    scope_config: dict[str, Any] = Field(default_factory=dict)


class ERPConnectionUpdate(BaseModel):
    name: Optional[str] = None
    sync_frequency: Optional[str] = None
    scope_config: Optional[dict[str, Any]] = None


class ERPConnectionOut(BaseModel):
    id: str
    name: str
    erp_type: ERPType
    url: str
    db_name: str
    username: str
    status: ERPSyncStatus
    last_sync_at: Optional[datetime]
    last_error: Optional[str]
    sync_frequency: str
    created_at: datetime

    class Config:
        from_attributes = True


class ERPTestConnectionResult(BaseModel):
    success: bool
    message: str


class ERPFieldMappingOut(BaseModel):
    id: str
    odoo_model: str
    source_field: str
    target_field: str
    transform: Optional[str]
    is_auto_learned: bool

    class Config:
        from_attributes = True


class ERPSyncLogOut(BaseModel):
    id: str
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    records_extracted: int
    error_message: Optional[str]

    class Config:
        from_attributes = True


class ERPSyncTriggerResult(BaseModel):
    sync_log_id: str
    status: str
    records_extracted: int