"""
debug_ocr.py — script isole pour diagnostiquer l'OCR sur UNE image, sans
passer par le serveur FastAPI ni le LLM. Utile pour voir precisement ce
que PaddleOCR (fr et ar) recupere sur un document donne, et a quelle
orientation.

Usage :
    python debug_ocr.py chemin/vers/la/facture.jpg
"""
import sys
from pathlib import Path
from PIL import Image
from paddleocr import PaddleOCR


def ocr_text(engine, image_path: str) -> str:
    try:
        result = engine.ocr(image_path, cls=True)
    except TypeError:
        result = engine.ocr(image_path)
    if not result:
        return ""
    lines = []
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


def main(image_path: str):
    print(f"Chargement des moteurs OCR (fr + ar)...")
    fr_engine = PaddleOCR(use_angle_cls=True, lang="fr", show_log=False)
    ar_engine = PaddleOCR(use_angle_cls=True, lang="ar", show_log=False)

    img = Image.open(image_path)
    print(f"Image : {image_path} ({img.size[0]}x{img.size[1]})")

    for angle in (0, 90, 180, 270):
        rotated_path = image_path
        if angle != 0:
            rotated = img.rotate(-angle, expand=True)
            rotated_path = f"{image_path}._test_rot{angle}.png"
            rotated.save(rotated_path)

        text_fr = ocr_text(fr_engine, rotated_path)
        text_ar = ocr_text(ar_engine, rotated_path)

        print(f"\n{'='*60}")
        print(f"ROTATION {angle}°")
        print(f"{'='*60}")
        print(f"--- FR ({len(text_fr)} car.) ---")
        print(text_fr[:500] or "(vide)")
        print(f"\n--- AR ({len(text_ar)} car.) ---")
        print(text_ar[:500] or "(vide)")

        if angle != 0:
            Path(rotated_path).unlink(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_ocr.py chemin/vers/image.jpg")
        sys.exit(1)
    main(sys.argv[1])