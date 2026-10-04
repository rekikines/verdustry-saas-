from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.modules.auth.models import User, Site
from app.modules.auth.router import get_current_user
from app.modules.sources.models import DataSource
from app.modules.validation.models import Extraction
from app.modules.iot.models import IoTDevice, IoTReading, IoTDeviceStatus

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

# Catégories affichées dans la page Sources (DataSource.category est une
# chaîne libre choisie à la création de la source, commune à tous les
# types ERP/IoT/Document/CSV/...).
SOURCE_CATEGORIES = ["Achats", "Énergie", "Eau", "Déchets", "Transport", "Stocks", "RH", "Auto"]


@router.get("/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    company = user.company_id

    total_sources = (
        db.query(func.count(DataSource.id))
        .filter(DataSource.company_id == company)
        .scalar()
        or 0
    )
    active_sources = (
        db.query(func.count(DataSource.id))
        .filter(DataSource.company_id == company, DataSource.status == "ACTIVE")
        .scalar()
        or 0
    )
    ocr_pending_sources = (
        db.query(func.count(DataSource.id))
        .filter(DataSource.company_id == company, DataSource.status == "OCR_PENDING")
        .scalar()
        or 0
    )
    pending_validation = (
        db.query(func.count(Extraction.id))
        .filter(Extraction.company_id == company, Extraction.status == "PENDING")
        .scalar()
        or 0
    )
    sites_count = (
        db.query(func.count(Site.id))
        .filter(Site.company_id == company)
        .scalar()
        or 0
    )

    # --- Répartition par catégorie, toutes sources confondues -----------
    category_breakdown = []
    for category in SOURCE_CATEGORIES:
        sources_count = (
            db.query(func.count(DataSource.id))
            .filter(DataSource.company_id == company, DataSource.category == category)
            .scalar()
            or 0
        )
        active_count = (
            db.query(func.count(DataSource.id))
            .filter(
                DataSource.company_id == company,
                DataSource.category == category,
                DataSource.status == "ACTIVE",
            )
            .scalar()
            or 0
        )
        extractions_count = (
            db.query(func.count(Extraction.id))
            .filter(Extraction.company_id == company, Extraction.category == category)
            .scalar()
            or 0
        )
        if sources_count == 0:
            continue
        category_breakdown.append({
            "category": category,
            "sources_count": sources_count,
            "active_sources_count": active_count,
            "records_count": extractions_count,
        })

    # --- Dernière mesure IoT PAR DEVICE (plusieurs capteurs actifs par
    # catégorie s'affichent désormais chacun séparément, ex. température
    # ET humidité pour un même DHT22, au lieu d'un seul par catégorie) ---
    iot_devices_status = []
    active_devices = (
        db.query(IoTDevice)
        .filter(IoTDevice.company_id == company, IoTDevice.status == IoTDeviceStatus.active)
        .all()
    )
    for device in active_devices:
        latest = (
            db.query(IoTReading)
            .filter(IoTReading.device_id == device.id)
            .order_by(IoTReading.timestamp.desc())
            .first()
        )
        category_value = device.category.value if hasattr(device.category, "value") else device.category
        iot_devices_status.append({
            "device_id": str(device.id),
            "device_name": device.name,
            "category": category_value,
            "latest_value": latest.value if latest else None,
            "latest_unit": device.unit,
            "latest_timestamp": latest.timestamp.isoformat() if latest else None,
        })

    return {
        "total_sources": total_sources,
        "active_sources": active_sources,
        "ocr_pending_sources": ocr_pending_sources,
        "pending_validation": pending_validation,
        "sites_count": sites_count,
        "category_breakdown": category_breakdown,
        "iot_devices": iot_devices_status,
    }