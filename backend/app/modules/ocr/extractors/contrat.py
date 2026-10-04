from .base import extract_amount, extract_date, extract_ref, field_conf
import re

def extract(text: str) -> tuple[dict[str, str], dict[str, float]]:
    fields, conf = {}, {}
    ref = extract_ref(text)
    if ref:
        fields["N° Contrat"] = ref
        conf["N° Contrat"] = 0.85
    amt = extract_amount(text)
    if amt:
        fields["Montant"] = amt
        conf["Montant"] = 0.85
    d = extract_date(text)
    if d:
        fields["Date"] = d
        conf["Date"] = 0.8
    m = re.search(r"Dur[ée]e\s*[:\s]*([^\n]{2,40})", text, re.I)
    if m:
        fields["Durée"] = m.group(1).strip()[:40]
        conf["Durée"] = 0.8
    m = re.search(r"Parties\s*[:\s]*([^\n]{5,100})", text, re.I)
    if m:
        fields["Parties"] = m.group(1).strip()[:100]
        conf["Parties"] = 0.75
    return {k: v for k, v in fields.items() if v}, conf