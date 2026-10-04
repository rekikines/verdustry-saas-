from .base import extract_date, extract_ref, field_conf
import re

def extract(text: str) -> tuple[dict[str, str], dict[str, float]]:
    fields, conf = {}, {}
    ref = extract_ref(text)
    if ref:
        fields["N°"] = ref
        conf["N°"] = 0.85
    d = extract_date(text)
    if d:
        fields["Date"] = d
        conf["Date"] = 0.85
    m = re.search(r"Objet\s*[:\s]*([^\n]{3,100})", text, re.I)
    if m:
        fields["Objet"] = m.group(1).strip()[:100]
        conf["Objet"] = 0.85
    if re.search(r"\bANPE\b", text, re.I):
        fields["Émetteur"] = "ANPE"
        conf["Émetteur"] = 0.9
    else:
        m = re.search(r"Émetteur\s*[:\s]*([^\n]{3,70})", text, re.I)
        if m:
            fields["Émetteur"] = m.group(1).strip()[:70]
            conf["Émetteur"] = 0.8
    return {k: v for k, v in fields.items() if v}, conf