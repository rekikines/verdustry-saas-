# app/modules/erp/mapping.py
from typing import Any
from .category_fields import config_for


def resolve_field(record: dict[str, Any], source_field: str):
    value = record.get(source_field)
    # Odoo renvoie les many2one sous forme [id, "Nom affiché"]
    if isinstance(value, list) and len(value) == 2:
        return value[1]
    return value


def apply_mapping(raw_records: list[dict], field_map: dict[str, str]) -> list[dict]:
    mapped = []
    for record in raw_records:
        item = {"_erp_id": record.get("id")}
        for source_field, target_field in field_map.items():
            item[target_field] = resolve_field(record, source_field)
        mapped.append(item)
    return mapped


def get_mapping_for(connection_id, category: str, db_session) -> dict[str, str]:
    """
    Charge le mapping personnalise/appris (US 24) pour une categorie,
    sinon retombe sur la config par defaut de category_fields.py.
    """
    from .models import ERPFieldMapping  # import local, évite les cycles

    config = config_for(category)
    if not config:
        return {}

    custom = (
        db_session.query(ERPFieldMapping)
        .filter_by(connection_id=connection_id, odoo_model=config["odoo_model"])
        .all()
    )
    if custom:
        return {m.source_field: m.target_field for m in custom}
    return config["field_map"]