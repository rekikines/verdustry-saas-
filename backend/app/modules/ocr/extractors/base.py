from __future__ import annotations
import re
from typing import Optional

def clean_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\u00a0", " ")).strip()

def find_first(patterns: list[str], text: str, flags=re.I) -> Optional[re.Match]:
    for p in patterns:
        m = re.search(p, text, flags)
        if m:
            return m
    return None

def extract_amount(text: str) -> Optional[str]:
    patterns = [
        r"Montant\s*à\s*payer\s*[:\s]*([0-9][0-9\s.,]*)\s*(TND|DT|Dinar|€|EUR)?",
        r"Total\s*TTC\s*[:\s]*([0-9][0-9\s.,]*)\s*(TND|DT|€|EUR)?",
        r"Montant\s*TTC\s*[:\s]*([0-9][0-9\s.,]*)\s*(TND|DT|€|EUR)?",
        r"Net\s*à\s*payer\s*[:\s]*([0-9][0-9\s.,]*)\s*(TND|DT|€|EUR)?",
        r"Montant\s*[:\s]*([0-9][0-9\s.,]*)\s*(TND|DT|€|EUR)",
    ]
    m = find_first(patterns, text)
    if not m:
        return None
    unit = (m.group(2) if m.lastindex and m.lastindex >= 2 and m.group(2) else "TND")
    return f"{clean_spaces(m.group(1))} {unit}"

def extract_date(text: str) -> Optional[str]:
    patterns = [
        r"(?:Date|du|le)\s*[:\s]*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})",
        r"(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})",
    ]
    m = find_first(patterns, text)
    return m.group(1) if m else None

def extract_period(text: str) -> Optional[str]:
    m = re.search(
        r"P[ée]riode\s*[:\s]*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\s*[–\-à]+\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})",
        text,
        re.I,
    )
    if m:
        return f"{m.group(1)} – {m.group(2)}"
    return None

def extract_ref(text: str) -> Optional[str]:
    patterns = [
        r"R[ée]f[ée]rence\s*[:\s]*([A-Z0-9][A-Z0-9\s\-/]{3,})",
        r"N[°o]?\s*(?:de\s*)?Facture\s*[:\s]*([A-Z0-9][A-Z0-9\s\-/]{2,})",
        r"N[°o]?\s*Contrat\s*[:\s]*([A-Z0-9][A-Z0-9\s\-/]{2,})",
        r"N[°o]?\s*[:\s]*([A-Z]{2,}-?\d{3,}[A-Z0-9\-]*)",
    ]
    m = find_first(patterns, text)
    return clean_spaces(m.group(1))[:50] if m else None

def field_conf(value: Optional[str], base: float = 0.85) -> float:
    if not value:
        return 0.0
    return base