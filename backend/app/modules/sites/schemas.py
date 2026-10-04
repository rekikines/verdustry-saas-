from pydantic import BaseModel, Field


class SiteCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    location: str | None = None


class SiteUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    location: str | None = None


class SiteOut(BaseModel):
    id: str
    name: str
    location: str | None = None
    company_id: str

    class Config:
        from_attributes = True