from .base import extract_amount, extract_date, extract_period, extract_ref, find_first, field_conf
import re

def extract(text: str) -> tuple[dict[str, str], dict[str, float]]:
    fields, conf = {}, {}

    amt = extract_amount(text)
    if amt:
        fields["Montant"] = amt
        conf["Montant"] = field_conf(amt, 0.9)

    m = re.search(r"(\d+[.,]?\d*)\s*kWh", text, re.I)
    if m:
        fields["Consommation"] = f"{m.group(1)} kWh"
        conf["Consommation"] = 0.9

    per = extract_period(text)
    if per:
        fields["Période"] = per
        conf["Période"] = 0.85
    else:
        d = extract_date(text)
        if d:
            fields["Date"] = d
            conf["Date"] = 0.8

    ref = extract_ref(text)
    if ref:
        fields["Référence"] = ref
        conf["Référence"] = 0.85

    fields["Fournisseur"] = "STEG" if re.search(r"\bSTEG\b", text, re.I) else fields.get("Fournisseur", "")
    if fields.get("Fournisseur"):
        conf["Fournisseur"] = 0.95

    m = re.search(r"District\s*[:\s]*([A-Za-zÀ-ÿ\s\-]{2,40})", text, re.I)
    if m:
        fields["District"] = m.group(1).strip()
        conf["District"] = 0.8

    m = re.search(r"(?:Client|Abonn[ée])\s*[:\s]*([^\n]{3,70})", text, re.I)
    if m:
        fields["Client"] = m.group(1).strip()[:70]
        conf["Client"] = 0.75

    fields = {k: v for k, v in fields.items() if v}
    return fields, conf