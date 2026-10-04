from .base import extract_amount, extract_date, extract_ref, field_conf
import re

def extract(text: str) -> tuple[dict[str, str], dict[str, float]]:
    fields, conf = {}, {}
    amt = extract_amount(text)
    if amt:
        fields["Montant"] = amt
        conf["Montant"] = 0.88
    ref = extract_ref(text)
    if ref:
        fields["N° Facture"] = ref
        conf["N° Facture"] = 0.85
    d = extract_date(text)
    if d:
        fields["Date"] = d
        conf["Date"] = 0.85
    m = re.search(r"Fournisseur\s*[:\s]*([^\n]{3,70})", text, re.I)
    if m:
        fields["Fournisseur"] = m.group(1).strip()[:70]
        conf["Fournisseur"] = 0.85
    return {k: v for k, v in fields.items() if v}, conf