"""
app/modules/ocr/llm_extract.py

Client generique compatible OpenAI (Groq ou tout fournisseur equivalent),
configure via app.core.config.settings.

Point important : les noms de champs affiches a l'utilisateur (category_fields.py)
contiennent des accents, parentheses, slashs ("Consommation (kWh)", "N°
depannage / compteur"...). Utilises tels quels comme CLES d'un schema JSON
pour du tool-calling force, ils font parfois echouer la generation du modele
(erreur 'tool_use_failed', failed_generation vide). On utilise donc des cles
techniques "slugifiees" (ex: consommation_kwh) pour le schema envoye au LLM,
puis on les remappe vers les vrais libelles avant de renvoyer le resultat.

FIX 1 (facture STEG classee "Achats" au lieu de "Energie") : indice par
mots-cles (keyword_rules.keyword_classify) injecte dans le prompt de
classification, avec une regle explicite STEG/SONEDE.

FIX 2 (v1, ABANDONNE) : "type": ["string", "null"] dans le schema pour
tolerer les valeurs null renvoyees par le modele sur les champs absents.
Resultat : Groq (contrairement a OpenAI) ne supporte pas les types-tableau
dans le schema d'un tool - l'outil devient invalide et le modele ne peut
plus l'appeler DU TOUT (erreur "did not call a tool", failed_generation
vide). Revert vers "type": "string" simple.

FIX 2 (v2, actif) : le schema reste strict ("type": "string"), mais le code
recupere desormais le JSON que le modele a quand meme tente de generer
depuis le champ 'failed_generation' de l'erreur API, quand il est present -
au lieu d'abandonner et de tout perdre au profit du palier 3 (regles),
beaucoup plus pauvre. Les valeurs null a l'interieur de ce JSON recupere
sont filtrees normalement (meme filtre "if value" que le cas nominal).
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.ocr.category_fields import CATEGORY_FIELDS, fields_for
from app.modules.ocr.keyword_rules import keyword_classify

try:
    from openai import OpenAI
    _client = (
        OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
        if settings.llm_api_key
        else None
    )
except ImportError:
    _client = None

MODEL = settings.llm_model

DOC_TYPES = [
    "Facture énergie", "Facture eau", "Bordereau déchets", "Contrat",
    "Attestation", "Facture fournisseur", "Facture client", "Bon de commande",
    "Document",
]

CLASSIFY_TOOL = {
    "type": "function",
    "function": {
        "name": "classify_document",
        "description": "Classifie un document industriel/environnemental.",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_type": {"type": "string", "enum": DOC_TYPES},
                "category": {"type": "string", "enum": list(CATEGORY_FIELDS.keys())},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "reasoning": {"type": "string", "description": "Explication en une phrase courte, 15 mots maximum."},
            },
            "required": ["doc_type", "category", "confidence"],
        },
    },
}

CLASSIFY_SYSTEM = (
    "Tu classifies des documents industriels a partir d'un texte OCR "
    "potentiellement bruite. Base-toi uniquement sur le contenu fourni. "
    "Assure la coherence entre doc_type et category : une 'Facture fournisseur' "
    "(l'entreprise achete) va avec la categorie Achats ; une 'Facture client' "
    "(l'entreprise vend) va avec la categorie Ventes. "
    "\n\n"
    "REGLE PRIORITAIRE - factures d'utilities (energie/eau) : une facture "
    "emise par un fournisseur d'energie ou d'eau (STEG, SONEDE, ou toute "
    "facture mentionnant une consommation en kWh, m3, un index de compteur, "
    "un district/circonscription) est TOUJOURS 'Facture énergie'/'Énergie' "
    "ou 'Facture eau'/'Eau' - JAMAIS 'Facture fournisseur'/'Achats', meme si "
    "elle contient aussi un N° de facture, un Total TTC ou un IBAN comme "
    "n'importe quelle facture. Cette regle s'applique AUSSI quand le "
    "document est majoritairement en arabe : une facture mentionnant "
    "des mots comme 'كهرباء' (electricite), 'الكهرباء والغاز' (STEG) ou "
    "'مياه' / 'معاليم مياه' (frais d'eau, SONEDE) est Energie ou Eau, "
    "jamais 'Comptabilité' ou 'Achats' generique, meme si le texte OCR "
    "est majoritairement compose de codes et de nombres peu lisibles. "
    "Le champ 'Indice mots-cles' fourni ci-dessous reflete un detecteur "
    "fiable pour ce cas precis (francais et arabe) : ne t'en ecarte que si "
    "le texte le contredit clairement. "
    "\n\n"
    "\n\n"
    "CAS DU TEXTE OCR TRES DEGRADE : si le texte est majoritairement en "
    "caracteres arabes mal reconnus (fragments incoherents, lettres "
    "isolees, aucun mot clairement lisible), NE choisis PAS 'Comptabilité' "
    "par defaut - c'est un choix par facilite qui est presque toujours "
    "faux dans ce cas (ces documents sont en realite le plus souvent des "
    "factures STEG/SONEDE illisibles, jamais des documents comptables). "
    "Dans ce cas, choisis ta meilleure hypothese entre 'Énergie' et 'Eau' "
    "si un indice meme faible existe (chiffres ressemblant a un index de "
    "compteur, structure de facture avec dates+montants), et donne une "
    "confidence BASSE (0.2 a 0.35) pour signaler qu'une verification "
    "humaine est necessaire - plutot qu'une confidence moyenne sur une "
    "categorie generique probablement fausse. "
    "Reponds UNIQUEMENT via l'appel d'outil classify_document, sans texte libre."
)

EXTRACT_SYSTEM = (
    "Tu extrais des champs structures d'un document industriel a partir de "
    "texte OCR, potentiellement bruite ou incomplet (photo de mauvaise "
    "qualite, texte melange). N'extrais un champ QUE s'il est explicitement "
    "present dans le texte - ne devine jamais une valeur. "
    "IMPORTANT : pour un champ que tu ne trouves pas, tu DOIS quand meme "
    "fournir une valeur de type texte pour respecter le format demande - "
    "utilise une chaine vide \"\" (jamais null, jamais le mot 'null', jamais "
    "le mot 'aucun'). "
    "Reponds UNIQUEMENT via l'appel d'outil extract_fields, sans texte libre."
)

_ACCENTS = {
    "é": "e", "è": "e", "ê": "e", "à": "a", "â": "a", "ô": "o",
    "ù": "u", "î": "i", "ç": "c", "°": "", "³": "3",
}


def _slugify(label: str) -> str:
    """Transforme un libelle affichable en cle technique sure pour un schema JSON."""
    s = label.lower()
    for a, b in _ACCENTS.items():
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "champ"


def _field_key_map(category: str) -> dict[str, str]:
    """slug -> libelle affichable, pour une categorie donnee."""
    return {_slugify(label): label for label in fields_for(category)}


def llm_available() -> bool:
    return _client is not None


def _build_extraction_tool(category: str) -> dict:
    key_map = _field_key_map(category)
    return {
        "type": "function",
        "function": {
            "name": "extract_fields",
            "description": f"Extrait les champs pertinents pour la categorie '{category}'.",
            "parameters": {
                "type": "object",
                "properties": {
                    # "type": "string" simple - Groq rejette le tool entier si
                    # on utilise un type-tableau ["string", "null"] (voir note
                    # FIX 2 v1/v2 en tete de fichier). Le cote "champ absent"
                    # est gere par le prompt (chaine vide) + la recuperation
                    # depuis failed_generation en cas d'echec malgre tout.
                    slug: {"type": "string", "description": label}
                    for slug, label in key_map.items()
                },
                "additionalProperties": False,
            },
        },
    }


def _keyword_hint(text: str) -> str:
    """Construit la ligne d'indice mots-cles injectee dans le prompt de
    classification. Un score de 0 signale au LLM que l'indice n'est pas
    fiable (aucun mot-cle trouve) et qu'il doit juger par lui-meme."""
    doc_type, category, score, _conf = keyword_classify(text)
    if score == 0:
        return "Indice mots-clés : aucun signal fort détecté — juge uniquement sur le texte."
    return (
        f"Indice mots-clés (détecteur automatique, {score} mot(s)-clé(s) trouvé(s)) : "
        f"doc_type='{doc_type}', category='{category}'."
    )


def _few_shot_examples(db: Optional[Session], category: str, limit: int = 3) -> str:
    if db is None:
        return ""

    from app.modules.validation.models import Extraction

    examples = (
        db.query(Extraction)
        .filter(Extraction.category == category, Extraction.status == "VALIDATED")
        .order_by(Extraction.created_at.desc())
        .limit(limit)
        .all()
    )
    if not examples:
        return ""

    blocks = []
    for ex in examples:
        if ex.raw_text:
            blocks.append(
                f"Texte :\n{ex.raw_text[:800]}\nChamps corrects attendus : {ex.fields}"
            )
        else:
            blocks.append(f"Champs corrects attendus pour ce type : {ex.fields}")

    return (
        "\n\nExemples de documents deja verifies par un humain pour cette "
        "categorie (imite ce niveau de precision) :\n\n" + "\n\n---\n\n".join(blocks)
    )


def _extract_tool_call_args(completion, expected_name: str) -> Optional[dict]:
    message = completion.choices[0].message
    if not message.tool_calls:
        return None
    for call in message.tool_calls:
        if call.function.name == expected_name:
            try:
                return json.loads(call.function.arguments)
            except json.JSONDecodeError:
                return None
    return None


def _salvage_partial_json(fragment: str) -> Optional[dict]:
    """
    Dernier recours quand le JSON est tronque (reponse coupee par
    max_tokens avant la fin) et que json.loads() echoue meme sur le
    fragment recupere. On scanne le texte a la recherche de toutes les
    paires "cle": "valeur" completes, en ignorant la derniere paire
    eventuellement coupee en plein milieu - au lieu de tout perdre pour
    UN champ mal termine.
    """
    pairs = re.findall(r'"([a-zA-Z0-9_]+)"\s*:\s*"((?:[^"\\]|\\.)*)"', fragment)
    if not pairs:
        return None
    return {key: value for key, value in pairs}


def _recover_args_from_error(exc: Exception) -> Optional[dict]:
    """
    Quand l'appel echoue avec une erreur de validation/parsing du tool
    call, Groq renvoie souvent (pas toujours) le JSON que le modele avait
    quand meme genere dans error.failed_generation - parfois tronque car
    coupe par max_tokens avant la fin. On tente de le recuperer, y compris
    partiellement, plutot que de tout perdre au profit du palier suivant
    (regles), beaucoup plus pauvre.

    Retourne None si rien n'est recuperable (l'appelant doit alors gerer
    l'echec normalement, ex: repli sur le palier suivant).
    """
    failed_generation = None

    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        failed_generation = (body.get("error") or {}).get("failed_generation")

    if not failed_generation:
        match = re.search(r"'failed_generation':\s*'((?:[^'\\]|\\.)*)'", str(exc))
        if match:
            try:
                failed_generation = match.group(1).encode().decode("unicode_escape")
            except Exception:
                failed_generation = None

    if not failed_generation:
        return None

    # 1) JSON valide (cas normal, l'erreur avait une autre cause que la troncature)
    try:
        payload = json.loads(failed_generation)
        if isinstance(payload, dict) and "arguments" in payload:
            return payload["arguments"]
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    # 2) JSON tronque (reponse coupee par max_tokens) : on sauve les paires completes
    return _salvage_partial_json(failed_generation)


def classify_with_llm(text: str, filename: str = "") -> Optional[dict[str, Any]]:
    if not llm_available() or not text or len(text.strip()) < 5:
        return None
    try:
        hint = _keyword_hint(text)
        completion = _client.chat.completions.create(
            model=MODEL,
            # FIX : 400 etait parfois trop juste quand le modele redige un
            # "reasoning" plus long que prevu - la reponse se faisait couper
            # avant la fin, produisant un JSON tronque et faisant echouer
            # TOUTE la classification (erreur "Failed to parse tool call
            # arguments as JSON"), pas seulement le champ reasoning.
            # FIX : les modeles a raisonnement (gpt-oss-120b...) consomment
            # une partie du budget pour "reflechir" en interne avant de
            # repondre - avec 700, tout le budget part parfois dans cette
            # reflexion et rien ne reste pour la reponse (echec avec
            # failed_generation vide, "did not call a tool").
            max_tokens=1800,
            temperature=0,
            messages=[
                {"role": "system", "content": CLASSIFY_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Nom de fichier : {filename or 'inconnu'}\n\n"
                        f"{hint}\n\n"
                        f"Texte OCR :\n---\n{text[:6000]}\n---"
                    ),
                },
            ],
            tools=[CLASSIFY_TOOL],
            tool_choice={"type": "function", "function": {"name": "classify_document"}},
        )
        result = _extract_tool_call_args(completion, "classify_document")

        if result is not None:
            print(f"[LLM] classify hint={hint!r} -> result category={result.get('category')} doc_type={result.get('doc_type')}")

        return result
    except Exception as e:
        # FIX : meme filet de secours que pour l'extraction - si le JSON de
        # classification a ete tronque (ex: reasoning trop long malgre
        # max_tokens=1800), on tente de recuperer doc_type/category/confidence
        # depuis failed_generation plutot que de perdre toute la classification
        # et de retomber sur les regles (moins fiables sur les documents
        # ambigus, precisement le cas ou on aurait le plus besoin du LLM).
        recovered = _recover_args_from_error(e)
        if recovered and recovered.get("doc_type") and recovered.get("category"):
            recovered.setdefault("confidence", 0.5)
            print(f"[LLM] classify recupere apres erreur : category={recovered.get('category')} doc_type={recovered.get('doc_type')}")
            return recovered
        print(f"[LLM] classification echouee : {e}")
        return None


def extract_fields_with_llm(
    text: str, category: str, db: Optional[Session] = None
) -> Optional[dict[str, str]]:
    if not llm_available() or not text:
        return None

    key_map = _field_key_map(category)
    few_shot = _few_shot_examples(db, category)

    try:
        completion = _client.chat.completions.create(
            model=MODEL,
            # 1200 etait trop juste pour les categories a beaucoup de champs
            # (Energie = 24 champs) : la reponse se faisait couper avant la
            # fin, produisant un JSON tronque et invalide (erreur "Failed to
            # parse tool call arguments as JSON"). 2500 laisse de la marge
            # meme pour Energie ; _salvage_partial_json reste en filet de
            # secours si un document extreme depasse quand meme cette limite.
            max_tokens=3500,
            temperature=0,
            messages=[
                {"role": "system", "content": EXTRACT_SYSTEM},
                {
                    "role": "user",
                    "content": f"Texte OCR :\n---\n{text[:6000]}\n---{few_shot}",
                },
            ],
            tools=[_build_extraction_tool(category)],
            tool_choice={"type": "function", "function": {"name": "extract_fields"}},
        )
        args = _extract_tool_call_args(completion, "extract_fields")
        recovered = False
    except Exception as e:
        args = _recover_args_from_error(e)
        recovered = args is not None
        if not recovered:
            print(f"[LLM] extraction des champs echouee (non recuperable) : {e}")
            return None

    if args is None:
        return None

    # filtre les valeurs vides/null/"null" litteral (le prompt demande "",
    # mais on reste defensif si le modele renvoie quand meme autre chose),
    # et ne garde que les cles reellement attendues pour cette categorie -
    # utile quand args vient de _salvage_partial_json, qui peut capter des
    # cles hors schema (ex: "name": "extract_fields") sur un JSON tronque.
    filled = {
        key_map[slug]: value
        for slug, value in args.items()
        if slug in key_map
        and value
        and str(value).strip().lower() not in ("null", "none", "aucun", "n/a")
    }

    print(
        f"[LLM] extract cat={category} "
        f"champs_trouves={len(filled)}/{len(key_map)} "
        f"few_shot={'oui' if few_shot else 'non'} "
        f"recupere_apres_erreur={recovered} "
        f"raw_text_preview={text[:300]!r}"
    )

    return filled


def extract_with_llm(
    text: str, filename: str = "", db: Optional[Session] = None
) -> Optional[dict[str, Any]]:
    classification = classify_with_llm(text, filename)
    if classification is None:
        return None

    category = classification["category"]
    fields = extract_fields_with_llm(text, category, db=db)
    if fields is None:
        return None

    return {
        "doc_type": classification["doc_type"],
        "category": category,
        "confidence": round(float(classification["confidence"]), 2),
        "fields": fields,
        "reasoning": classification.get("reasoning", ""),
        "_source": "llm",
    }