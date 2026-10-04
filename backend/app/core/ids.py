"""
Générateur d'identifiants préfixés, cohérent avec vos conventions
(ext-, erp-, site-...). Si un utilitaire équivalent existe déjà dans
app/core (par ex. app/core/ids.py), supprimez ce fichier et importez
le vôtre à la place dans les modules ci-dessous.
"""

import secrets


def generate_id(prefix: str, length: int = 12) -> str:
    """Génère un ID du type '<prefix>-<hex>' (ex: 'iot-4f9a2c8b1e3d')."""
    return f"{prefix}-{secrets.token_hex(length // 2)}"
