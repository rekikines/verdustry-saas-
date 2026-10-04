def resolve_path(record, path: str):
    """Resout un chemin en notation pointee dans du JSON imbrique.
    Supporte les index de liste : 'items.0.price'"""
    current = record
    for part in path.split("."):
        if current is None:
            return None
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def apply_mapping(raw_records: list[dict], field_map: dict[str, str]) -> list[dict]:
    mapped = []
    for record in raw_records:
        item = {source and resolve_path(record, src): None for src in []}  # placeholder, corrige ci-dessous
        item = {}
        for source_path, target_field in field_map.items():
            item[target_field] = resolve_path(record, source_path)
        mapped.append(item)
    return mapped


def extract_records(payload, data_path: str) -> list[dict]:
    """Extrait le tableau d'enregistrements depuis la reponse JSON complete."""
    if not data_path:
        return payload if isinstance(payload, list) else []
    node = resolve_path(payload, data_path)
    return node if isinstance(node, list) else []