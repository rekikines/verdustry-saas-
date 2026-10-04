"""
app/modules/ocr/vision_extract.py

Extraction directement depuis l'IMAGE du document (LLM multimodal/vision),
sans passer par l'OCR texte-plat classique (PaddleOCR/Tesseract).

Pourquoi : l'OCR texte-plat detruit la mise en page - un tableau devient
une suite de lignes desordonnees, un melange francais/arabe devient un
bruit incoherent, une inversion RTL casse les mots arabes, l'ecriture
manuscrite est rarement bien reconnue, et des annotations manuelles
(cercles rouges, surlignage) sont lues comme si c'etait du texte du
document. Le LLM en aval recoit alors des fragments decroches de leur
contexte et invente une association plausible plutot que d'avouer qu'il
ne sait pas.

HISTORIQUE :
- v1 : un seul appel avec un schema JSON strict geant (tool-calling, 150+
  proprietes) - trop lourd pour qwen/qwen3.6-27b sur Groq (echec).
- v2 : separe en 2 appels (classification puis extraction), + passage a
  Gemini (fournisseur separe, voir plus bas) en mode JSON libre.
- v3 (ACTUELLE) : fusionne a nouveau en 1 SEUL appel. Raison : le quota
  gratuit Gemini limite le nombre de REQUETES par jour (pas les tokens) -
  2 appels par document divisait par 2 le nombre de documents testables/
  jour. Un appel combine (classification + extraction dans le meme JSON)
  double le nombre de documents traitables avec le meme quota. Possible
  maintenant qu'on est en JSON libre (pas de schema strict par outil) -
  le probleme de "schema trop gros" de la v1 ne s'applique plus.

Utilise en Palier 0 dans service.py : si l'extraction visuelle reussit
avec une confiance suffisante ET au moins un champ trouve, on s'arrete la.
Sinon, repli normal sur le pipeline existant (OCR texte -> LLM texte ->
classificateur local -> regles par mots-cles).
"""
from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.modules.ocr.category_fields import CATEGORY_FIELDS, fields_for

# La vision pointe vers un fournisseur SEPARE de Groq (settings.llm_*,
# utilise pour le texte) - Groq n'a pas de modele fiable pour images+JSON
# parmi ceux testes sur ce compte. Ajoutez ces 3 cles a votre .env :
#   LLM_VISION_API_KEY=<cle API de votre fournisseur vision>
#   LLM_VISION_BASE_URL=<ex: https://generativelanguage.googleapis.com/v1beta/openai ou https://api.openai.com/v1>
#   LLM_VISION_MODEL=<ex: gemini-3.6-flash, gpt-4o-mini>
# Tant que ces cles ne sont pas definies, la vision reste desactivee
# (vision_available() renvoie False) et le pipeline OCR texte prend le
# relais automatiquement - rien ne casse en attendant.
try:
    from openai import OpenAI

    _vision_api_key = getattr(settings, "llm_vision_api_key", None)
    _vision_base_url = getattr(settings, "llm_vision_base_url", None)

    _client = (
        OpenAI(api_key=_vision_api_key, base_url=_vision_base_url)
        if _vision_api_key
        else None
    )
except ImportError:
    _client = None

VISION_MODEL = getattr(settings, "llm_vision_model", None) or "gpt-4o-mini"

DOC_TYPES = [
    "Facture énergie", "Facture eau", "Bordereau déchets", "Contrat",
    "Attestation", "Facture fournisseur", "Facture client", "Bon de commande",
    "Document",
]

_MIME_TYPES = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".bmp": "image/bmp", ".tif": "image/tiff", ".tiff": "image/tiff",
}


# Etat en memoire (reinitialise a chaque redemarrage du serveur) : une fois
# le quota JOURNALIER Gemini epuise, inutile de retenter un appel a chaque
# document jusqu'au lendemain - ca perd du temps et pollue les logs d'une
# erreur 429 previsible. On desactive la vision jusqu'au reset estime.
_vision_disabled_until: Optional[datetime] = None


def vision_available() -> bool:
    global _vision_disabled_until
    if _client is None:
        return False
    if _vision_disabled_until is not None:
        if datetime.now(timezone.utc) < _vision_disabled_until:
            return False
        print("[Vision] periode de desactivation quota terminee — nouvelle tentative autorisee")
        _vision_disabled_until = None
    return True


def _disable_vision_until_tomorrow() -> None:
    global _vision_disabled_until
    # Estimation prudente : le quota "per day" de Google se reinitialise a
    # minuit (fuseau du projet, generalement Pacific Time) - on vise le
    # minuit UTC suivant + marge, plutot que de connaitre le fuseau exact.
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=10, second=0, microsecond=0
    )
    _vision_disabled_until = tomorrow
    print(
        f"[Vision] quota journalier épuisé — vision désactivée jusqu'à "
        f"{tomorrow.isoformat()} (évite des appels inutiles en attendant)"
    )


def _encode_image(image_path: Path) -> Optional[str]:
    try:
        data = image_path.read_bytes()
        mime = _MIME_TYPES.get(image_path.suffix.lower(), "image/jpeg")
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        print(f"[Vision] encodage image echoue: {e}")
        return None


def _parse_json_response(content: str) -> Optional[dict]:
    """Parse tolerant pour les reponses JSON d'un modele vision. Certains
    modeles (dont Gemini par moments) encadrent leur JSON de balises
    markdown (```json ... ```) ou ajoutent du texte autour malgre la
    consigne "reponds uniquement en JSON" - un json.loads() strict echoue
    alors avec des erreurs comme "Unterminated string..."."""
    if not content:
        return None

    text = content.strip()

    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _is_quota_error(exc: Exception) -> bool:
    """Detecte une erreur de quota/limite de requetes (429) plutot qu'une
    vraie erreur d'extraction, pour logger clairement la difference -
    sinon on a l'air de "regresser" sur un document alors que c'est juste
    le quota gratuit journalier qui est epuise (independant du document)."""
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower()


def _is_daily_quota_error(exc: Exception) -> bool:
    """Distingue un quota JOURNALIER (inutile de reessayer avant demain,
    voir _disable_vision_until_tomorrow) d'une limite plus fine (ex: par
    minute) qui se debloquerait toute seule en quelques secondes - dans ce
    dernier cas on ne desactive rien, on retentera simplement au prochain
    document."""
    msg = str(exc)
    return "PerDay" in msg or "per_day" in msg.lower() or "requests per day" in msg.lower()


# ---------------------------------------------------------------------------
# Prompt combine : classification + extraction en 1 seul appel
# ---------------------------------------------------------------------------

def _build_categories_reference() -> str:
    """Liste compacte categorie -> champs attendus, inseree dans le prompt
    (pas de schema JSON strict par outil - juste une reference textuelle,
    le modele choisit lui-meme quels champs remplir selon la categorie
    qu'il a retenue)."""
    lines = []
    for cat, labels in CATEGORY_FIELDS.items():
        lines.append(f"- {cat} : {', '.join(labels)}")
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "Tu regardes l'image d'un document industriel/administratif tunisien "
    "(facture STEG, SONEDE, facture fournisseur, bordereau dechets...). "
    "Quelle que soit sa langue (francais, arabe, ou melange), sa qualite "
    "(photo inclinee, floue, manuscrite) ou la presence d'annotations "
    "manuelles (cercles rouges, surlignage, feutre) - ignore ces "
    "annotations, elles sont ajoutees APRES coup par une personne et ne "
    "font PAS partie des donnees imprimees du document : ne les recopie "
    "jamais comme si c'etait une valeur du document.\n\n"
    "Une facture STEG ou SONEDE se reconnait a son en-tete/logo/mise en "
    "page meme si le texte est majoritairement en arabe - classe-la "
    "'Énergie' ou 'Eau' en consequence, jamais 'Comptabilité' par defaut.\n\n"
    "Identifie precisement quel LIBELLE correspond a quelle VALEUR selon "
    "la position reelle dans le tableau/la mise en page - ne melange "
    "jamais deux colonnes ou deux lignes differentes. Si une valeur n'est "
    "pas clairement lisible ou que l'association libelle/valeur est "
    "incertaine, n'inclus PAS ce champ plutot que de deviner.\n\n"
    "Categories disponibles et champs attendus pour chacune :\n"
    f"{_build_categories_reference()}\n\n"
    f"Types de document possibles : {DOC_TYPES}\n\n"
    "Reponds UNIQUEMENT avec un objet JSON de cette forme exacte, sans "
    "texte ni balise markdown autour :\n"
    '{"doc_type": "<un type de la liste>", "category": "<une categorie de la liste>", '
    '"confidence": <nombre entre 0 et 1>, "fields": {"<libelle exact>": "<valeur>", ...}}\n'
    "Les cles de \"fields\" doivent etre EXACTEMENT les libelles de la categorie "
    "choisie (recopies tels quels, en francais) - n'inclus que ceux dont tu es sur."
)


def extract_from_image(image_path: Path) -> Optional[dict[str, Any]]:
    if not vision_available():
        return None

    data_uri = _encode_image(image_path)
    if data_uri is None:
        return None

    try:
        completion = _client.chat.completions.create(
            model=VISION_MODEL,
            # Modeles a raisonnement (gemini-3.6-flash...) : une partie du
            # budget part dans la reflexion interne avant la reponse - un
            # budget trop bas coupe la reponse avant meme le premier champ.
            max_tokens=3000,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Classifie ce document et extrais tous les champs visibles."},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                },
            ],
        )
        content = completion.choices[0].message.content
        if not content:
            print("[Vision] reponse vide")
            return None
        result = _parse_json_response(content)
        if result is None:
            print(f"[Vision] JSON illisible meme apres nettoyage : {content[:200]!r}")
            return None
    except Exception as e:
        if _is_quota_error(e):
            print(f"[Vision] QUOTA EPUISE (pas un bug document) : {e}")
            if _is_daily_quota_error(e):
                _disable_vision_until_tomorrow()
        else:
            print(f"[Vision] extraction echouee : {e}")
        return None

    doc_type = result.get("doc_type", "Document")
    category = result.get("category", "Achats")
    confidence = result.get("confidence", 0.5)
    raw_fields = result.get("fields") or {}

    valid_labels = set(fields_for(category))
    fields = {
        label: value
        for label, value in raw_fields.items()
        if label in valid_labels and value and str(value).strip().lower() not in ("null", "none", "aucun", "n/a")
    }

    print(f"[Vision] cat={category} type={doc_type} conf={confidence} champs_trouvés={len(fields)}")

    return {
        "doc_type": doc_type,
        "category": category,
        "confidence": round(float(confidence), 2) if isinstance(confidence, (int, float)) else 0.5,
        "fields": fields,
    }