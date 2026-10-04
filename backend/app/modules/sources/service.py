from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.auth.models import Site, User
from app.modules.sources.models import DataSource

from app.modules.erp import service as erp_service
from app.modules.erp.schemas import ERPConnectionCreate
from app.modules.erp.models import ERPConnection

from app.modules.external_api import service as api_service
from app.modules.external_api.schemas import APIConnectionCreate
from app.modules.external_api.models import APIConnection


def _default_status(source_type: str) -> str:
    if source_type == "DOCUMENT":
        return "OCR_PENDING"
    if source_type == "MANUAL":
        return "INACTIVE"
    return "ACTIVE"


def list_sources(db: Session, user: User, site_id: str | None = None) -> list[DataSource]:
    q = db.query(DataSource).filter(DataSource.company_id == user.company_id)
    sid = site_id or user.site_id
    if sid:
        q = q.filter(DataSource.site_id == sid)
    return q.order_by(DataSource.created_at.desc()).all()


def create_source(
    db: Session,
    user: User,
    name: str,
    type_: str,
    category: str,
    site_id: str,
    config: dict | None = None,
) -> DataSource:
    site = (
        db.query(Site)
        .filter(Site.id == site_id, Site.company_id == user.company_id)
        .first()
    )
    if not site:
        raise HTTPException(400, detail="Site invalide pour cette société.")

    config = config or {}
    status = _default_status(type_)
    stored_config: dict = {}

    # ── Cas particulier ERP : on crée la vraie connexion dans le module erp ──
    if type_ == "ERP":
        required = ["url", "db_name", "username", "password"]
        missing = [f for f in required if not config.get(f)]
        if missing:
            raise HTTPException(
                400, detail=f"Champs ERP manquants : {', '.join(missing)}"
            )

        connection = erp_service.create_connection(
            db,
            user.company_id,
            ERPConnectionCreate(
                name=name.strip(),
                erp_type=config.get("erp_type", "odoo"),
                site_id=site_id,
                url=config["url"].strip(),
                db_name=config["db_name"].strip(),
                username=config["username"].strip(),
                password=config["password"],
                sync_frequency=config.get("sync_frequency", "daily"),
                scope_config={"categories": config.get("categories", [category])},
            ),
        )

        # Test de connexion immédiat pour donner un statut réaliste dès la création
        ok, message = erp_service.test_connection(db, connection)
        status = "ACTIVE" if ok else "FAILED"
        stored_config = {"erp_connection_id": connection.id}
        if not ok:
            stored_config["last_error"] = message

    # ── Cas particulier API externe : on crée la connexion dans le module external_api ──
    elif type_ == "API":
        if not config.get("base_url"):
            raise HTTPException(400, detail="Champ 'base_url' manquant pour une source API.")

        connection = api_service.create_connection(
            db,
            user.company_id,
            APIConnectionCreate(
                name=name.strip(),
                category=category,
                site_id=site_id,
                base_url=config["base_url"],
                endpoint_path=config.get("endpoint_path", ""),
                http_method=config.get("http_method", "GET"),
                query_params=config.get("query_params", {}),
                auth_type=config.get("auth_type", "none"),
                credentials=config.get("credentials"),
                response_data_path=config.get("response_data_path", ""),
                pagination_type=config.get("pagination_type", "none"),
                pagination_config=config.get("pagination_config", {}),
                field_map=config.get("field_map", {}),
                sync_frequency=config.get("sync_frequency", "daily"),
            ),
        )

        ok, message = api_service.test_connection(db, connection)
        status = "ACTIVE" if ok else "FAILED"
        stored_config = {"api_connection_id": connection.id}
        if not ok:
            stored_config["last_error"] = message

    else:
        stored_config = config

    row = DataSource(
        id=f"ds-{uuid4().hex[:12]}",
        name=name.strip(),
        type=type_,
        category=category.strip() or "Achats",
        status=status,
        volume="—" if status == "OCR_PENDING" else "0",
        config=stored_config,
        site_id=site_id,
        company_id=user.company_id,
        last_sync_at=datetime.utcnow() if status == "ACTIVE" else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_source(db: Session, user: User, source_id: str) -> None:
    row = (
        db.query(DataSource)
        .filter(
            DataSource.id == source_id,
            DataSource.company_id == user.company_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(404, detail="Source introuvable.")

    # Supprimer aussi la connexion ERP liée, si elle existe
    if row.type == "ERP" and row.config and row.config.get("erp_connection_id"):
        conn = (
            db.query(ERPConnection)
            .filter_by(id=row.config["erp_connection_id"], company_id=user.company_id)
            .first()
        )
        if conn:
            db.delete(conn)

    # Supprimer aussi la connexion API liée, si elle existe
    if row.type == "API" and row.config and row.config.get("api_connection_id"):
        conn = (
            db.query(APIConnection)
            .filter_by(id=row.config["api_connection_id"], company_id=user.company_id)
            .first()
        )
        if conn:
            db.delete(conn)

    db.delete(row)
    db.commit()


def sync_source(db: Session, user: User, source_id: str) -> DataSource:
    row = (
        db.query(DataSource)
        .filter(
            DataSource.id == source_id,
            DataSource.company_id == user.company_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(404, detail="Source introuvable.")
    if row.type in ("DOCUMENT", "MANUAL", "CSV"):
        raise HTTPException(400, detail="Ce type ne supporte pas la synchronisation auto.")

    if row.type == "ERP":
        connection_id = (row.config or {}).get("erp_connection_id")
        if not connection_id:
            raise HTTPException(400, detail="Connexion ERP introuvable pour cette source.")

        connection = (
            db.query(ERPConnection)
            .filter_by(id=connection_id, company_id=user.company_id)
            .first()
        )
        if not connection:
            raise HTTPException(404, detail="Connexion ERP introuvable.")

        log = erp_service.run_sync(db, connection, data_source_id=row.id)

        row.status = "ACTIVE" if log.status == "success" else "FAILED"
        row.volume = f"{log.records_extracted} enreg."
        row.last_sync_at = connection.last_sync_at or datetime.utcnow()
        db.commit()
        db.refresh(row)
        return row

    if row.type == "API":
        connection_id = (row.config or {}).get("api_connection_id")
        if not connection_id:
            raise HTTPException(400, detail="Connexion API introuvable pour cette source.")

        connection = (
            db.query(APIConnection)
            .filter_by(id=connection_id, company_id=user.company_id)
            .first()
        )
        if not connection:
            raise HTTPException(404, detail="Connexion API introuvable.")

        log = api_service.run_sync(db, connection, data_source_id=row.id)

        row.status = "ACTIVE" if log.status == "success" else "FAILED"
        row.volume = f"{log.records_extracted} enreg."
        row.last_sync_at = connection.last_sync_at or datetime.utcnow()
        db.commit()
        db.refresh(row)
        return row

    row.status = "ACTIVE"
    row.last_sync_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row