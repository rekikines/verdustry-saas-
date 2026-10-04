from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine

from app.modules.auth.router import router as auth_router
import app.modules.auth.models

from app.modules.sites.router import router as sites_router

from app.modules.sources.router import router as sources_router
import app.modules.sources.models

from app.modules.validation.router import router as validation_router
import app.modules.validation.models

from app.modules.dashboard.router import router as dashboard_router

from app.modules.ocr.router import router as ocr_router

from app.modules.erp.router import router as erp_router
import app.modules.erp.models
from app.modules.erp.scheduler import start_scheduler, load_existing_connections

from app.modules.iot.router import router as iot_router

from app.modules.external_api.router import router as external_api_router
import app.modules.external_api.models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Verdustry API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(sites_router)
app.include_router(sources_router)
app.include_router(validation_router)
app.include_router(dashboard_router)
app.include_router(ocr_router)
app.include_router(erp_router)
app.include_router(iot_router)
app.include_router(external_api_router)


@app.get("/health")
def health():
    return {"status": "ok", "modules": ["auth"]}


@app.on_event("startup")
def _start_erp_scheduler():
    start_scheduler()
    load_existing_connections()