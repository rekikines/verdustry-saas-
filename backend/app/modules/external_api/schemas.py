from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from .models import AuthType, APISyncStatus


class APIConnectionCreate(BaseModel):
    name: str
    category: str = "Achats"
    site_id: Optional[str] = None
    base_url: str
    endpoint_path: str = ""
    http_method: str = "GET"
    query_params: dict[str, Any] = Field(default_factory=dict)
    request_body: Optional[dict[str, Any]] = None
    auth_type: AuthType = AuthType.none
    credentials: Optional[dict[str, str]] = None
    response_data_path: str = ""
    pagination_type: str = "none"
    pagination_config: dict[str, Any] = Field(default_factory=dict)
    field_map: dict[str, str] = Field(default_factory=dict)
    sync_frequency: str = "daily"


class APIConnectionOut(BaseModel):
    id: str
    name: str
    category: str
    base_url: str
    endpoint_path: str
    auth_type: AuthType
    status: APISyncStatus
    last_sync_at: Optional[datetime]
    last_error: Optional[str]
    sync_frequency: str
    created_at: datetime

    class Config:
        from_attributes = True


class APITestConnectionResult(BaseModel):
    success: bool
    message: str


class APISyncTriggerResult(BaseModel):
    sync_log_id: str
    status: str
    records_extracted: int