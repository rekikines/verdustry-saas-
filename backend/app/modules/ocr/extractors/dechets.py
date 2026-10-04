from .base import extract_date, extract_ref, field_conf
import re

def extract(text: str) -> tuple[dict[str, str], dict[str, float]]:
    fields, conf = {}, {}

    m = re.search(r"(\d+[.,]?\d*)\s*(?:t|tonnes?)\b", text, re.I)
    if m:
        fields["Quantité"] = f"{m.group(1)} t"
        conf["Quantité"] = 0.9

    d = extract_date(text)
    if d:
        fields["Date"] = d
        conf["Date"] = 0.85

    m = re.search(r"Transporteur\s*[:\s]*([^\n]{3,70})", text, re.I)
    if m:
        fields["Transporteur"] = m.group(1).strip()[:70]
        conf["Transporteur"] = 0.85

    m = re.search(r"Producteur\s*[:\s]*([^\n]{3,70})", text, re.I)
    if m:
        fields["Producteur"] = m.group(1).strip()[:70]
        conf["Producteur"] = 0.8

    m = re.search(r"(?:Type|Nature)\s*(?:de\s*d[ée]chets?)?\s*[:\s]*([^\n]{3,60})", text, re.I)
    if m:
        fields["Type déchets"] = m.group(1).strip()[:60]
        conf["Type déchets"] = 0.8

    ref = extract_ref(text)
    if ref:
        fields["Référence"] = ref
        conf["Référence"] = 0.8

    return {k: v for k, v in fields.items() if v}, conf