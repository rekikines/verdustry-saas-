"""
OCR Verdustry — Tesseract (principal) + PaddleOCR optionnel pour le texte brut.
Classification + extraction : 3 paliers, du plus intelligent au plus robuste :
  1) LLM (classification + extraction de champs specifiques a la categorie)
  2) Classificateur local entraine sur vos documents valides (categorie seule)
  3) Regles par mots-cles + regex (filet de secours ultime, toujours disponible)

FIX (facture SONEDE classee "Comptabilité" au lieu de "Eau") : PaddleOCR
n'etait instancie qu'en francais (lang="fr"). Beaucoup de factures
tunisiennes (STEG, SONEDE) sont majoritairement en arabe - sur ces
documents, l'OCR francais ne recuperait presque rien d'exploitable, et le
LLM devait deviner la categorie a l'aveugle sur un texte quasi vide. On
instancie desormais un second moteur PaddleOCR en arabe (lang="ar") et on
fusionne les deux textes avant classification/extraction.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Optional
from sqlalchemy.orm import Session
from PIL import Image, ImageOps, ImageStat

from app.modules.ocr.llm_extract import extract_with_llm, llm_available
from app.modules.ocr.train_classifier import predict_with_local_model
from app.modules.ocr.category_fields import fields_for
from app.modules.ocr.keyword_rules import keyword_classify
from app.modules.ocr.vision_extract import extract_from_image, vision_available

# ── Chemins Windows ─────────────────────────────────────────────
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler-26.02.0\Library\bin"

_paddle_fr = None
_paddle_ar = None
_tesseract_ok = False

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    pytesseract.get_tesseract_version()
    _tesseract_ok = True
except Exception:
    _tesseract_ok = False

try:
    from pdf2image import convert_from_path
    _pdf2image_ok = True
except Exception:
    _pdf2image_ok = False


def _get_paddle_fr():
    """Instance PaddleOCR francais (documents/parties en francais)."""
    global _paddle_fr
    if _paddle_fr is not None:
        return _paddle_fr
    try:
        from paddleocr import PaddleOCR
        use_gpu = os.getenv("PADDLE_USE_GPU", "0") == "1"
        _paddle_fr = PaddleOCR(use_angle_cls=True, lang="fr", show_log=False, use_gpu=use_gpu)
        print(f"[OCR] PaddleOCR (fr) prêt (gpu={use_gpu})")
        return _paddle_fr
    except Exception as e:
        print(f"[OCR] PaddleOCR (fr) indisponible: {e}")
        return None


def _get_paddle_ar():
    """Instance PaddleOCR arabe - necessaire pour les factures STEG/SONEDE
    tunisiennes majoritairement en arabe (ex: factures d'eau SONEDE)."""
    global _paddle_ar
    if _paddle_ar is not None:
        return _paddle_ar
    try:
        from paddleocr import PaddleOCR
        use_gpu = os.getenv("PADDLE_USE_GPU", "0") == "1"
        _paddle_ar = PaddleOCR(use_angle_cls=True, lang="ar", show_log=False, use_gpu=use_gpu)
        print(f"[OCR] PaddleOCR (ar) prêt (gpu={use_gpu})")
        return _paddle_ar
    except Exception as e:
        print(f"[OCR] PaddleOCR (ar) indisponible: {e}")
        return None


def is_ocr_available() -> bool:
    return _tesseract_ok or _get_paddle_fr() is not None or _get_paddle_ar() is not None


def engine_name() -> str:
    if _get_paddle_fr() is not None or _get_paddle_ar() is not None:
        return "paddleocr"
    if _tesseract_ok:
        return "tesseract"
    return "simulation"

def tesseract_available() -> bool:
    return _tesseract_ok


def _ocr_paddle_with(engine, image_path: str) -> str:
    """Execute un moteur PaddleOCR deja instancie (fr ou ar) sur une image."""
    if engine is None:
        return ""
    try:
        result = engine.ocr(image_path, cls=True)
    except TypeError:
        result = engine.ocr(image_path)
    except Exception as e:
        print(f"[OCR] paddle ocr failed: {e}")
        return ""

    lines: list[str] = []
    if not result:
        return ""
    for page in result:
        if not page:
            continue
        for item in page:
            try:
                txt = item[1][0]
                if txt and str(txt).strip():
                    lines.append(str(txt).strip())
            except Exception:
                continue
    return "\n".join(lines)


def _pdf_to_images(file_path: Path) -> list[Image.Image]:
    """Convertit un PDF en liste d'images PIL (une par page), via poppler."""
    if not _pdf2image_ok:
        print("[OCR] pdf2image indisponible — impossible de convertir le PDF en images")
        return []
    try:
        return convert_from_path(str(file_path), poppler_path=POPPLER_PATH)
    except Exception as e:
        print(f"[OCR] conversion PDF->images echouee: {e}")
        return []


def _ocr_tesseract_image(image: Image.Image, lang: str = "fra") -> str:
    """Execute Tesseract sur une image PIL, retourne le texte brut.
    lang="fra+ara" combine les deux packs de langue si le pack arabe est
    installe (necessite `ara.traineddata` dans le dossier tessdata de
    Tesseract - a installer separement si absent)."""
    try:
        return pytesseract.image_to_string(image, lang=lang)
    except Exception as e:
        print(f"[OCR] tesseract failed (lang={lang}): {e}")
        return ""


def _score_text(text: str) -> float:
    """Score heuristique de qualite d'un texte OCR, utilise pour comparer
    plusieurs orientations d'une meme image (0/90/180/270°). Les mots-cles
    metier reconnus comptent beaucoup plus que la longueur brute, qui peut
    etre gonflee par du bruit."""
    if not text:
        return 0.0
    _, _, kw_score, _ = keyword_classify(text)
    return len(text) + kw_score * 100


def _find_best_rotation(image_path: str, fr_engine) -> tuple[str, bool]:
    """Teste les 4 orientations (0/90/180/270°) avec le moteur francais
    (rapide, sert juste a reperer le bon sens) et renvoie le chemin de
    l'image la plus lisible. Beaucoup de photos de factures prises au
    telephone sont dans le mauvais sens - l'OCR echoue presque totalement
    sur une image mal orientee, quels que soient le moteur et la langue.
    Retourne (chemin, a_ete_tourne)."""
    if fr_engine is None:
        return image_path, False

    try:
        img = Image.open(image_path)
    except Exception:
        return image_path, False

    best_path, best_score, best_angle = image_path, -1.0, 0
    temp_paths: list[str] = []

    for angle in (0, 90, 180, 270):
        if angle == 0:
            candidate_path = image_path
        else:
            rotated = img.rotate(-angle, expand=True)
            candidate_path = f"{image_path}._rot{angle}.png"
            rotated.save(candidate_path, "PNG")
            temp_paths.append(candidate_path)

        text = _ocr_paddle_with(fr_engine, candidate_path)
        score = _score_text(text)
        print(f"[OCR] test rotation {angle}° : score={score:.0f} ({len(text)} car.)")

        if score > best_score:
            best_path, best_score, best_angle = candidate_path, score, angle

    for p in temp_paths:
        if p != best_path:
            Path(p).unlink(missing_ok=True)

    if best_angle != 0:
        print(f"[OCR] rotation {best_angle}° retenue")
    return best_path, best_angle != 0


def _simulate(filename: str) -> str:
    """Filet de secours ultime quand aucun moteur OCR n'est disponible (ni
    PaddleOCR ni Tesseract) : evite de planter et laisse le pipeline de
    classification tourner sur un texte vide (confiance faible, mais le
    document est quand meme cree plutot que de renvoyer une erreur 500)."""
    print(f"[OCR] Aucun moteur OCR disponible pour {filename} — texte vide utilise.")
    return ""


def _preprocess_for_ocr(image_path: Path) -> Path:
    """Ameliore la lisibilite d'une photo de facture avant l'OCR classique
    (PaddleOCR/Tesseract). Beaucoup de factures tunisiennes (SONEDE
    notamment) sont imprimees a l'encre bleue sur fond blanc/creme, ce que
    les moteurs OCR generalistes lisent souvent mal (contraste plus faible
    qu'un texte noir classique, dilue par la conversion en niveaux de gris
    standard qui moyenne les 3 canaux).

    On isole le canal ROUGE : l'encre bleue y apparait tres sombre (elle
    contient tres peu de rouge) alors que le fond y reste clair - un bien
    meilleur contraste qu'une conversion en gris classique pour ce cas
    precis. On etire ensuite le contraste, on binarise (noir/blanc pur) et
    on agrandit legerement l'image si elle est petite.

    Ne modifie jamais le fichier original - retourne le chemin d'une image
    temporaire pretraitee (a nettoyer par l'appelant), ou le chemin
    d'origine si le pretraitement echoue."""
    try:
        img = Image.open(image_path).convert("RGB")

        # Agrandissement : aide l'OCR sur du texte petit/serre (frequent
        # sur les photos de factures prises au telephone, pas scannees)
        w, h = img.size
        if max(w, h) < 2000:
            scale = 2000 / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        # Canal rouge = meilleur contraste pour de l'encre bleue (voir
        # docstring). Pour de l'encre noire classique, ca reste un niveau
        # de gris raisonnable (le noir a du rouge faible aussi), donc ce
        # traitement n'aggrave pas les documents deja lisibles.
        r, _, _ = img.split()
        gray = ImageOps.autocontrast(r, cutoff=1)

        # Binarisation (noir/blanc pur) - seuil simple base sur la moyenne
        threshold = ImageStat.Stat(gray).mean[0] * 0.85
        bw = gray.point(lambda p: 255 if p > threshold else 0)

        out_path = image_path.parent / f"_prep_{image_path.stem}.png"
        bw.save(out_path, "PNG")
        return out_path
    except Exception as e:
        print(f"[OCR] pretraitement image echoue: {e}")
        return image_path


def extract_text(file_path: Path) -> tuple[str, str]:
    suffix = file_path.suffix.lower()
    paths: list[str] = []
    temp: list[Path] = []
    rotated_temp_files: list[str] = []
    preprocessed_temp_files: list[str] = []
    try:
        if suffix == ".pdf":
            for i, page in enumerate(_pdf_to_images(file_path)):
                tmp = file_path.parent / f"_page_{i}.png"
                page.save(tmp, "PNG")
                paths.append(str(tmp))
                temp.append(tmp)
        else:
            paths.append(str(file_path))

        # Pretraitement (contraste, binarisation, agrandissement) avant tout
        # passage OCR classique - voir _preprocess_for_ocr. Vise notamment
        # les factures a l'encre bleue (SONEDE) mal lues sinon. Le fichier
        # original (paths) reste intact et sert toujours pour la vision.
        ocr_paths: list[str] = []
        for p in paths:
            prep_path = _preprocess_for_ocr(Path(p))
            ocr_paths.append(str(prep_path))
            if str(prep_path) != p:
                preprocessed_temp_files.append(str(prep_path))

        fr_engine = _get_paddle_fr()
        text_fr = "\n".join(_ocr_paddle_with(fr_engine, p) for p in ocr_paths).strip() if fr_engine else ""

        # FIX v4 : compter les "mots" alphabetiques etait encore trompeur -
        # l'OCR francais, force sur de l'arabe, invente des suites de lettres
        # latines sans aucun sens ("Wall+)", "aallaicae"...) qui passaient le
        # test haut la main. On reutilise plutot le detecteur de mots-cles
        # (keyword_rules) : s'il ne trouve AUCUN mot-cle connu dans le texte
        # francais, c'est un bien meilleur signal que le francais n'a rien
        # capte d'exploitable, et qu'il faut tenter l'arabe en complement.
        _, _, kw_score_fr, _ = keyword_classify(text_fr)

        if kw_score_fr > 0:
            text = text_fr
            print(f"[OCR] paddle fr={len(text_fr)} car, {kw_score_fr} mot(s)-clé(s) détecté(s) — passage arabe ignoré")
        else:
            ar_engine = _get_paddle_ar()
            text_ar = "\n".join(_ocr_paddle_with(ar_engine, p) for p in ocr_paths).strip() if ar_engine else ""
            text = "\n".join(t for t in (text_fr, text_ar) if t).strip()
            print(f"[OCR] paddle fr={len(text_fr)} car (0 mot-clé) -> ar={len(text_ar)} car, fusion={len(text)} car")

            # FIX v5 : si meme fr+ar combines restent tres pauvres, l'image
            # est peut-etre tout simplement mal orientee (photo prise en
            # paysage, document scanne a l'envers...). Dernier recours,
            # seulement declenche ici pour ne pas alourdir le cas courant :
            # on teste les 4 rotations et on refait fr+ar sur la meilleure.
            if len(text) < 40:
                print("[OCR] texte encore insuffisant — test des orientations (0/90/180/270°)")
                new_paths = []
                any_rotated = False
                for p in ocr_paths:
                    best_path, was_rotated = _find_best_rotation(p, fr_engine)
                    new_paths.append(best_path)
                    if was_rotated:
                        any_rotated = True
                        rotated_temp_files.append(best_path)

                if any_rotated:
                    text_fr_r = "\n".join(_ocr_paddle_with(fr_engine, p) for p in new_paths).strip() if fr_engine else ""
                    text_ar_r = "\n".join(_ocr_paddle_with(ar_engine, p) for p in new_paths).strip() if ar_engine else ""
                    text_r = "\n".join(t for t in (text_fr_r, text_ar_r) if t).strip()
                    print(f"[OCR] après rotation : fr={len(text_fr_r)} car, ar={len(text_ar_r)} car, fusion={len(text_r)} car")
                    if len(text_r) > len(text):
                        text = text_r

        if len(text) >= 8:
            return text, "paddleocr"

        if _tesseract_ok:
            text = "\n".join(_ocr_tesseract_image(Image.open(p), lang="fra+ara") for p in ocr_paths).strip()
            if len(text) >= 8:
                return text, "tesseract"

        return _simulate(file_path.name), "simulation"
    except Exception as e:
        print(f"[OCR] extract error: {e}")
        return _simulate(file_path.name), "simulation"
    finally:
        for t in temp:
            try:
                t.unlink(missing_ok=True)
            except Exception:
                pass
        for p in rotated_temp_files:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass
        for p in preprocessed_temp_files:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass


def _norm(s: str) -> str:
    s = (s or "").lower()
    for a, b in [
        ("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"), ("â", "a"),
        ("ô", "o"), ("ù", "u"), ("î", "i"), ("ç", "c"), ("°", " "), ("º", " "),
    ]:
        s = s.replace(a, b)
    return s


# ── Palier 3 : classification par mots-cles (filet de secours) ──
# Delegue a keyword_rules.keyword_classify, partage avec llm_extract.py
# (utilise la-bas comme indice pour le LLM au palier 1). Source de verite
# unique des regles : app/modules/ocr/keyword_rules.py

def classify_doc(text: str, filename: str = "") -> tuple[str, str, float]:
    doc_type, category, _score, confidence = keyword_classify(text)
    return doc_type, category, confidence


def parse_fields(text: str, category: str) -> dict[str, str]:
    """
    Extraction par regex - filet de secours. Retourne uniquement des champs
    generiques (pas specifiques par categorie, contrairement au palier LLM) :
    c'est la limite assumee du filet de secours.
    """
    fields: dict[str, str] = {}
    t = text or ""
    n = _norm(t)

    for p in [
        r"montant\s*a\s*payer\s*[:\s]*([0-9][0-9\s.,]*)\s*(tnd|dt|dinar|€|eur)?",
        r"total\s*ttc\s*[:\s]*([0-9][0-9\s.,]*)\s*(tnd|dt|€|eur)?",
        r"montant\s*ttc\s*[:\s]*([0-9][0-9\s.,]*)\s*(tnd|dt|€|eur)?",
        r"net\s*a\s*payer\s*[:\s]*([0-9][0-9\s.,]*)\s*(tnd|dt|€|eur)?",
        r"montant\s*[:\s]*([0-9][0-9\s.,]*)\s*(tnd|dt|€|eur)",
    ]:
        m = re.search(p, n, re.I)
        if m:
            unit = "TND"
            if m.lastindex and m.lastindex >= 2 and m.group(2):
                unit = m.group(2).upper().replace("DT", "TND")
            fields["Montant"] = f"{m.group(1).strip()} {unit}"
            break

    m = re.search(r"(\d+[.,]?\d*)\s*k\s*w\s*h", n, re.I)
    if m:
        fields["Consommation (kWh)"] = m.group(1)
    m = re.search(r"(\d+[.,]?\d*)\s*(?:t|tonnes?)\b", n, re.I)
    if m:
        fields["Quantité (t)"] = m.group(1)
    m = re.search(r"(\d+[.,]?\d*)\s*m[3³]", n, re.I)
    if m:
        fields["Consommation (m³)"] = m.group(1)

    m = re.search(r"(?:date|du|le)\s*[:\s]*(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})", n, re.I)
    if not m:
        m = re.search(r"(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4})", n)
    if m:
        fields["Période"] = m.group(1)

    if re.search(r"\bsteg\b", n):
        fields["Fournisseur"] = "STEG"
    elif re.search(r"\bsonede\b", n):
        fields["Fournisseur"] = "SONEDE"
    else:
        m = re.search(r"fournisseur\s*[:\s]*([^\n]{3,70})", t, re.I)
        if m:
            fields["Fournisseur"] = m.group(1).strip()[:70]

    allowed = set(fields_for(category)) | {"Montant", "Fournisseur"}
    return {k: v for k, v in fields.items() if k in allowed or not allowed}



def process_document(file_path: Path, db: Optional[Session] = None) -> dict[str, Any]:
    # Palier 0 : extraction visuelle directe (LLM multimodal sur l'image
    # elle-meme, sans OCR texte intermediaire). Contourne les limites
    # structurelles de l'OCR classique : tableaux desordonnes, melange
    # francais/arabe, ecriture manuscrite, annotations manuelles (cercles
    # rouges...). Voir vision_extract.py pour le detail.
    #
    # Pour un PDF, on convertit uniquement la 1ere page en image - un futur
    # ajustement possible serait d'essayer chaque page si la 1ere echoue.
    vision_image_path: Optional[Path] = None
    vision_temp_file: Optional[Path] = None
    if file_path.suffix.lower() == ".pdf":
        pages = _pdf_to_images(file_path)
        if pages:
            vision_temp_file = file_path.parent / f"_vision_{file_path.stem}.png"
            pages[0].save(vision_temp_file, "PNG")
            vision_image_path = vision_temp_file
    else:
        vision_image_path = file_path

    if vision_image_path is not None and vision_available():
        vision_result = extract_from_image(vision_image_path)
        if vision_temp_file is not None:
            vision_temp_file.unlink(missing_ok=True)

        if vision_result is not None and vision_result["confidence"] >= 0.5 and vision_result["fields"]:
            print(f"[OCR] source=vision cat={vision_result['category']} type={vision_result['doc_type']}")
            return {
                "raw_text": None,
                "ocr_mode": "vision",
                "extraction_source": "vision",
                "doc_type": vision_result["doc_type"],
                "category": vision_result["category"],
                "confidence": vision_result["confidence"],
                "fields": vision_result["fields"],
            }
        print("[OCR] vision insuffisante ou indisponible — repli sur le pipeline OCR texte")
    elif vision_temp_file is not None:
        vision_temp_file.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Repli : pipeline OCR texte existant (Palier 1 LLM texte -> Palier 2
    # classificateur local -> Palier 3 regles), inchange.
    # ------------------------------------------------------------------
    text, mode = extract_text(file_path)

    # DEBUG : verifie ce que l'OCR a effectivement lu, pour diagnostiquer
    # les cas de mauvaise extraction (texte manquant/mele vs LLM defaillant)
    print(f"[OCR] texte extrait ({len(text)} caracteres) : {text[:500]!r}")

    # Palier 1 : LLM (classification + extraction specifique, avec few-shot)
    llm_result = extract_with_llm(text, filename=file_path.name, db=db)
    if llm_result is not None:
        result = {
            "raw_text": text,
            "ocr_mode": mode,
            "extraction_source": "llm",
            "doc_type": llm_result["doc_type"],
            "category": llm_result["category"],
            "confidence": llm_result["confidence"],
            "fields": llm_result["fields"],
        }
        print(f"[OCR] source=llm cat={result['category']} type={result['doc_type']}")
        return result

    # Palier 2 : classificateur local entraine (categorie uniquement,
    # champs extraits ensuite par regex filtrees sur cette categorie)
    local_pred = predict_with_local_model(text)
    if local_pred is not None:
        category, local_conf = local_pred
        doc_type, _, _ = classify_doc(text)  # type de document via regles (pas couvert par le classif. local)
        fields = parse_fields(text, category)
        result = {
            "raw_text": text,
            "ocr_mode": mode,
            "extraction_source": "local_model",
            "doc_type": doc_type,
            "category": category,
            "confidence": round(local_conf, 2),
            "fields": fields,
        }
        print(f"[OCR] source=local_model cat={category} conf={local_conf:.2f}")
        return result

    # Palier 3 : regles par mots-cles (toujours disponible)
    doc_type, category, class_conf = classify_doc(text)
    fields = parse_fields(text, category)
    ocr_w = 0.9 if mode == "tesseract" else 0.45
    confidence = round(min(ocr_w * 0.5 + class_conf * 0.5, 0.98), 2)

    print(f"[OCR] source=rules mode={mode} cat={category} type={doc_type}")
    return {
        "raw_text": text,
        "ocr_mode": mode,
        "extraction_source": "rules",
        "doc_type": doc_type,
        "category": category,
        "confidence": confidence,
        "fields": fields,
    }