import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from .models import ERPConnection, ERPSyncLog, ERPSyncStatus, ERPType
from .schemas import ERPConnectionCreate
from .connectors.odoo import OdooConnector
from .security_vault import encrypt_value, decrypt_value
from .mapping import apply_mapping, get_mapping_for
from .category_fields import config_for
from .scheduler import schedule_connection, unschedule_connection


from app.modules.validation.models import Extraction


def _get_connector(connection: ERPConnection) -> OdooConnector:
    password = decrypt_value(connection.credentials_encrypted)
    if connection.erp_type == ERPType.odoo or connection.erp_type.value == "odoo":
        return OdooConnector(connection.url, connection.db_name, connection.username, password)
    raise NotImplementedError(f"Connecteur {connection.erp_type} non encore implémenté")


def create_connection(db: Session, company_id: str, data: ERPConnectionCreate) -> ERPConnection:
    connection = ERPConnection(
        company_id=company_id,
        site_id=data.site_id,
        name=data.name,
        erp_type=data.erp_type,
        url=data.url,
        db_name=data.db_name,
        username=data.username,
        credentials_encrypted=encrypt_value(data.password),
        sync_frequency=data.sync_frequency,
        scope_config=data.scope_config,
        status=ERPSyncStatus.pending,
  )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    schedule_connection(connection.id, connection.sync_frequency)  # ← ajout
    return connection


def test_connection(db: Session, connection: ERPConnection) -> tuple[bool, str]:
    try:
        connector = _get_connector(connection)
        ok = connector.test_connection()
        connection.status = ERPSyncStatus.connected if ok else ERPSyncStatus.error
        connection.last_error = None if ok else "Authentification refusée"
        db.commit()
        return ok, "Connexion réussie" if ok else "Authentification refusée"
    except Exception as e:
        connection.status = ERPSyncStatus.error
        connection.last_error = str(e)
        db.commit()
        return False, str(e)


def run_sync(db: Session, connection: ERPConnection, data_source_id: str | None = None) -> ERPSyncLog:
    """
    data_source_id : id de la DataSource (ds-xxxx) affichée dans le tableau
    Sources. Sert a tracer l'origine de chaque Extraction creee.
    """
    log = ERPSyncLog(connection_id=connection.id, status="running")
    db.add(log)
    db.commit()

    connection.status = ERPSyncStatus.syncing
    db.commit()

    total_extracted = 0
    try:
        connector = _get_connector(connection)
        categories = connection.scope_config.get("categories", ["Achats"])

        for category in categories:
            config = config_for(category)
            if not config:
                continue

            raw_records = connector.extract(
                model=config["odoo_model"],
                domain=config["domain_extra"],
                fields=list(config["field_map"].keys()),
                limit=500,
            )
            mapping_rules = get_mapping_for(connection.id, category, db)
            mapped_records = apply_mapping(raw_records, mapping_rules)

            for rec in mapped_records:
                erp_record_id = rec.pop("_erp_id", None)

                # Evite les doublons si on relance la meme sync plusieurs fois :
                # on utilise (source_id + category + erp_record_id) comme cle logique
                existing = None
                if data_source_id and erp_record_id is not None:
                    existing = (
                        db.query(Extraction)
                        .filter(
                            Extraction.source_id == data_source_id,
                            Extraction.category == category,
                            Extraction.fields["_erp_record_id"].as_string() == str(erp_record_id),
                        )
                        .first()
                    )

                if existing:
                    existing.fields = {**rec, "_erp_record_id": erp_record_id}
                    continue

                extraction = Extraction(
                    id=f"ext-{uuid.uuid4().hex[:12]}",
                    filename=_build_display_name(category, rec),
                    doc_type="ERP",
                    category=category,
                    status="PENDING",
                    confidence=1.0,
                    fields={**rec, "_erp_record_id": erp_record_id},
                    raw_text=None,
                    source_id=data_source_id,
                    site_id=connection.site_id,
                    company_id=connection.company_id,
                    created_at=datetime.utcnow(),
                )
                db.add(extraction)

            total_extracted += len(mapped_records)

        log.status = "success"
        log.records_extracted = total_extracted
        connection.status = ERPSyncStatus.connected
        connection.last_sync_at = datetime.utcnow()
        connection.last_error = None

    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
        connection.status = ERPSyncStatus.error
        connection.last_error = str(e)

    log.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(log)
    return log
def _build_display_name(category: str, rec: dict) -> str:
    ref = (
        rec.get("N° facture")
        or rec.get("Référence")
        or rec.get("Référence article")
        or ""
    )
    return f"ERP · {category}" + (f" · {ref}" if ref else "")