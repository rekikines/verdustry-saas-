import os
from openai import OpenAI

API_KEY = os.environ.get("GROQ_API_KEY") or os.environ.get("LLM_API_KEY")
BASE_URL = "https://api.groq.com/openai/v1"

if not API_KEY:
    print("Definissez GROQ_API_KEY (ou collez votre cle directement ci-dessous pour un test rapide).")
    API_KEY = input("Cle API Groq : ").strip()

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

models = client.models.list()

print(f"\n{len(models.data)} modèle(s) disponible(s) sur votre compte :\n")
for m in sorted(models.data, key=lambda x: x.id):
    print(f"  {m.id}")

print("\nCherchez un modèle dont le nom contient 'vision', 'scout', 'maverick' ou '4-'.")
print("Copiez le nom EXACT dans VISION_MODEL (app/modules/ocr/vision_extract.py).")