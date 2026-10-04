from . import energie, dechets, contrat, attestation, achats

_MAP = {
    "Facture énergie": energie.extract,
    "Facture eau": energie.extract,  # proche ; à spécialiser plus tard
    "Bordereau déchets": dechets.extract,
    "Contrat": contrat.extract,
    "Attestation": attestation.extract,
    "Facture fournisseur": achats.extract,
    "Document": achats.extract,
}

def extract_for(doc_type: str, text: str) -> tuple[dict[str, str], dict[str, float]]:
    fn = _MAP.get(doc_type, achats.extract)
    return fn(text)