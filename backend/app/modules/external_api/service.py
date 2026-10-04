import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from .models import APIConnection, APISyncLog, APISyncStatus
from .connectors.rest import RESTConnector
from .mapping import apply_mapping, extract_records, resolve_path
from app.modules.erp.security_vault import encrypt_value, decrypt_value  # reutilise le coffre-fort existant
from app.modules.validation.models import Extraction


def _get_connector(connection: APIConnection) -> RESTConnector:
    creds = {}
    if connection.credentials_encrypted:
        creds = json.loads(decrypt_value(connection.credentials_encrypted))
    auth_type = connection.auth_type.value if hasattr(connection.auth_type, "value") else connection.auth_type
    return RESTConnector(connection.base_url, auth_type, creds)


def create_connection(db: Session, company_id: str, data) -> APIConnection:
    connection = APIConnection(
        company_id=company_id,
        site_id=data.site_id,
        name=data.name,
        category=data.category,
        base_url=data.base_url.rstrip("/"),
        endpoint_path=data.endpoint_path,
        http_method=data.http_method,
        query_params=data.query_params or {},
        request_body=data.request_body,
        auth_type=data.auth_type,
        credentials_encrypted=encrypt_value(json.dumps(data.credentials)) if data.credentials else None,
        response_data_path=data.response_data_path,
        pagination_type=data.pagination_type,
        pagination_config=data.pagination_config or {},
        field_map=data.field_map or {},
        sync_frequency=data.sync_frequency,
        status=APISyncStatus.pending,
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


def test_connection(db: Session, connection: APIConnection) -> tuple[bool, str]:
    try:
        connector = _get_connector(connection)
        ok = connector.test_connection(connection.endpoint_path, connection.http_method, connection.query_params)
        connection.status = APISyncStatus.connected if ok else APISyncStatus.error
        connection.last_error = None if ok else "Le serveur a repondu avec une erreur"
        db.commit()
        return ok, "Connexion reussie" if ok else "Echec — verifiez l'URL et les identifiants"
    except Exception as e:
        connection.status = APISyncStatus.error
        connection.last_error = str(e)
        db.commit()
        return False, str(e)


def _paginate(connector: RESTConnector, connection: APIConnection) -> list[dict]:
    pconf = connection.pagination_config or {}

    if connection.pagination_type == "none":
        payload = connector.fetch_page(connection.endpoint_path, connection.http_method, connection.query_params, connection.request_body)
        return extract_records(payload, connection.response_data_path)

    all_records = []
    max_pages = pconf.get("max_pages", 50)  # garde-fou anti-boucle infinie

    if connection.pagination_type == "page":
        page_param = pconf.get("page_param", "page")
        size_param = pconf.get("size_param", "page_size")
        page_size = pconf.get("page_size", 100)
        page = pconf.get("start_page", 1)
        for _ in range(max_pages):
            params = {**(connection.query_params or {}), page_param: page, size_param: page_size}
            payload = connector.fetch_page(connection.endpoint_path, connection.http_method, params)
            page_records = extract_records(payload, connection.response_data_path)
            if not page_records:
                break
            all_records.extend(page_records)
            if len(page_records) < page_size:
                break
            page += 1
        return all_records

    if connection.pagination_type == "offset":
        offset_param = pconf.get("offset_param", "offset")
        limit_param = pconf.get("limit_param", "limit")
        limit = pconf.get("limit", 100)
        offset = 0
        for _ in range(max_pages):
            params = {**(connection.query_params or {}), offset_param: offset, limit_param: limit}
            payload = connector.fetch_page(connection.endpoint_path, connection.http_method, params)
            page_records = extract_records(payload, connection.response_data_path)
            if not page_records:
                break
            all_records.extend(page_records)
            if len(page_records) < limit:
                break
            offset += limit
        return all_records

    if connection.pagination_type == "cursor":
        cursor_param = pconf.get("cursor_param", "cursor")
        next_cursor_path = pconf.get("next_cursor_path", "next_cursor")
        cursor = None
        for _ in range(max_pages):
            params = dict(connection.query_params or {})
            if cursor:
                params[cursor_param] = cursor
            payload = connector.fetch_page(connection.endpoint_path, connection.http_method, params)
            page_records = extract_records(payload, connection.response_data_path)
            all_records.extend(page_records)
            cursor = resolve_path(payload, next_cursor_path)
            if not cursor or not page_records:
                break
        return all_records

    return all_records


def run_sync(db: Session, connection: APIConnection, data_source_id: str | None = None) -> APISyncLog:
    log = APISyncLog(connection_id=connection.id, status="running")
    db.add(log)
    db.commit()
    connection.status = APISyncStatus.syncing
    db.commit()

    try:
        connector = _get_connector(connection)
        raw_records = _paginate(connector, connection)
        mapped_records = apply_mapping(raw_records, connection.field_map or {})

        for rec in mapped_records:
            db.add(Extraction(
                id=f"ext-{uuid.uuid4().hex[:12]}",
                filename=f"API · {connection.category} · {connection.name}",
                doc_type="API",
                category=connection.category,
                status="PENDING",
                confidence=1.0,
                fields=rec,
                raw_text=None,
                source_id=data_source_id,
                site_id=connection.site_id,
                company_id=connection.company_id,
                created_at=datetime.utcnow(),
            ))

        log.status = "success"
        log.records_extracted = len(mapped_records)
        connection.status = APISyncStatus.connected
        connection.last_sync_at = datetime.utcnow()
        connection.last_error = None

    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
        connection.status = APISyncStatus.error
        connection.last_error = str(e)

    log.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(log)
    return log