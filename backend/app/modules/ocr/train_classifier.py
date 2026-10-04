"""
app/modules/ocr/train_classifier.py

Entraine un classificateur local (TF-IDF + regression logistique) sur les
Extraction au statut VALIDATED accumulees en base. A relancer periodiquement.

Usage :
    python -m app.modules.ocr.train_classifier
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from app.modules.ocr.keyword_rules import keyword_classify
 
from app.core.database import SessionLocal
from app.modules.validation.models import Extraction

MODEL_PATH = Path(__file__).parent / "local_classifier.joblib"
MIN_SAMPLES = 20


def _document_text(ex: Extraction) -> str:
    """
    Texte utilise pour l'entrainement. Prefere le texte OCR brut ; si une
    ancienne ligne ne l'a pas (creee avant l'ajout de la colonne raw_text),
    on se rabat sur les champs extraits concatenes - moins riche mais evite
    de perdre ces exemples.
    """
    if ex.raw_text and len(ex.raw_text.strip()) > 5:
        return ex.raw_text
    if ex.fields:
        return " ".join(str(v) for v in ex.fields.values() if v)
    return ""


def load_dataset() -> tuple[list[str], list[str]]:
    db = SessionLocal()
    try:
        docs = (
            db.query(Extraction)
            .filter(Extraction.status == "VALIDATED")
            .all()
        )
        texts, labels = [], []
        for d in docs:
            text = _document_text(d)
            if text:
                texts.append(text)
                labels.append(d.category)
        return texts, labels
    finally:
        db.close()


def train() -> dict:
    texts, labels = load_dataset()

    if len(texts) < MIN_SAMPLES:
        return {
            "trained": False,
            "reason": f"Seulement {len(texts)} documents valides, minimum {MIN_SAMPLES} requis.",
        }

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=3000, ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42,
        stratify=labels if len(set(labels)) > 1 else None,
    )

    pipeline.fit(X_train, y_train)
    accuracy = pipeline.score(X_test, y_test) if X_test else None

    joblib.dump(pipeline, MODEL_PATH)

    return {
        "trained": True,
        "samples": len(texts),
        "categories": sorted(set(labels)),
        "test_accuracy": round(accuracy, 3) if accuracy is not None else None,
        "model_path": str(MODEL_PATH),
    }


def predict_with_local_model(text: str) -> Optional[tuple[str, float]]:
    if not MODEL_PATH.exists():
        return None
    try:
        pipeline = joblib.load(MODEL_PATH)
        proba = pipeline.predict_proba([text])[0]
        idx = proba.argmax()
        category = pipeline.classes_[idx]
        confidence = float(proba[idx])
        return category, confidence
    except Exception as e:
        print(f"[Classifier local] prediction echouee : {e}")
        return None


if __name__ == "__main__":
    result = train()
    if result["trained"]:
        print(f"Modele entraine sur {result['samples']} documents.")
        print(f"Categories couvertes : {result['categories']}")
        print(f"Precision sur echantillon de test : {result['test_accuracy']}")
        print(f"Sauvegarde : {result['model_path']}")
    else:
        print(f"Entrainement non effectue : {result['reason']}")
