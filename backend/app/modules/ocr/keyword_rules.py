"""
app/modules/ocr/keyword_rules.py

Detecteur de categorie par mots-cles, extrait de service.py pour etre
partage entre :
  - service.py (palier 3 : filet de secours ultime)
  - llm_extract.py (indice fourni au LLM au palier 1, pour eviter les
    confusions Energie/Eau <-> Achats sur les factures STEG/SONEDE)

Isole dans son propre module pour eviter tout import circulaire entre
service.py et llm_extract.py.

FIX : ajout de mots-cles en arabe. Beaucoup de factures tunisiennes (STEG,
SONEDE) sont majoritairement en arabe - les mots-cles latins ("steg",
"sonede", "kwh") n'y apparaissent parfois pas du tout, ce qui faisait
tomber le detecteur (et donc l'indice fourni au LLM) a un score de 0 et
laissait le LLM deviner a l'aveugle sur un texte OCR degrade.
"""

_ACCENTS_NORM = [
    ("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"), ("â", "a"),
    ("ô", "o"), ("ù", "u"), ("î", "i"), ("ç", "c"), ("°", " "), ("º", " "),
]

# Ordre important : les regles les plus specifiques (Energie, Eau, Dechets)
# passent avant "Facture fournisseur" / Achats, qui est le cas generique.
# Mots-cles arabes ajoutes pour chaque categorie utility (electricite/eau),
# tires du vocabulaire standard des factures STEG/SONEDE.
RULES = [
    (
        "Facture énergie", "Énergie",
        [
            "steg", "electricite", "kwh", "montant a payer", "district", "compteur",
            # arabe : "Societe Tunisienne de l'Electricite et du Gaz", "electricite", "gaz", "consommation"
            "الشركة التونسية للكهرباء والغاز", "التونسية للكهرباء", "كهرباء", "استهلاك", "غاز",
        ],
    ),
    (
        "Facture eau", "Eau",
        [
            "sonede", "facture eau", "m3", "consommation d'eau",
            # arabe : "SONEDE" (Societe Nationale d'Exploitation et de Distribution des Eaux),
            # "frais/redevances eau", "total frais d'eau", "eau" - + termes
            # releves directement sur des factures SONEDE reelles (fevrier 2026)
            "الشركة الوطنية لاستغلال وتوزيع المياه", "معاليم مياه", "معاليم الماء", "مجموع معاليم الماء", "مياه",
            "معلوم قطع الماء",
            # FIX : mots-cles composes de plusieurs mots ("معاليم الماء") ne
            # matchent quasi jamais, car l'OCR restitue un mot par ligne -
            # la phrase complete n'apparait jamais comme substring continu.
            # "الماء" seul (le mot "eau" lui-meme) est beaucoup plus robuste :
            # il survit au decoupage ligne par ligne de l'OCR.
            "الماء",
        ],
    ),
    ("Bordereau déchets", "Déchets", ["bordereau", "dechet", "tonnes", "transporteur", "bsda"]),
    ("Contrat", "Achats", ["contrat", "convention", "avenant", "duree"]),
    ("Attestation", "Achats", ["attestation", "certificat", "conformite", "anpe"]),
    ("Facture fournisseur", "Achats", ["facture", "ttc", "fournisseur", "total ht"]),
]


def normalize(s: str) -> str:
    s = (s or "").lower()
    for a, b in _ACCENTS_NORM:
        s = s.replace(a, b)
    return s


def _reverse_lines(text: str) -> str:
    """PaddleOCR restitue parfois l'arabe avec l'ordre des caracteres
    inverse ligne par ligne (probleme connu de gestion RTL/bidi) - une
    ligne comme 'كوم ءيكم ءامل ءومجم' correspond en fait a une variante de
    'مجموع...الماء' une fois inversee caractere par caractere. On inverse
    chaque ligne independamment (jamais le texte entier, pour ne pas aussi
    inverser l'ordre des lignes elles-memes)."""
    return "\n".join(line[::-1] for line in (text or "").split("\n"))


def keyword_classify(text: str) -> tuple[str, str, int, float]:
    """Retourne (doc_type, category, score, confidence) selon les mots-cles
    trouves dans le texte. Score = nombre de mots-cles matches (utile pour
    juger la fiabilite de l'indice, pas seulement le resultat).

    Cherche a la fois dans le texte tel quel et dans sa version inversee
    ligne par ligne (voir _reverse_lines) pour capter les mots-cles arabes
    meme quand l'OCR les restitue a l'envers."""
    original = text or ""
    combined = original + "\n" + _reverse_lines(original)
    blob = normalize(combined)
    best = ("Document", "Achats", 0, 0.35)
    for doc_type, category, keys in RULES:
        score = sum(1 for k in keys if k in blob)
        if score > best[2]:
            conf = min(0.55 + score * 0.1, 0.95)
            best = (doc_type, category, score, conf)
    return best