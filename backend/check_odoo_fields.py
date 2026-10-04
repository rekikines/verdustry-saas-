# backend/check_odoo_fields.py
"""
Script de diagnostic - à lancer manuellement pour vérifier les noms de
champs réels disponibles sur une instance Odoo, avant de figer le
mapping dans category_fields.py.

Usage :
    python check_odoo_fields.py
"""
import xmlrpc.client
import json

# --- À remplir avec vos identifiants de test ---
URL = "https://votrenom.odoo.com"
DB = "votrenom"
USERNAME = "admin@votrenom.com"
PASSWORD = "votre_mot_de_passe"

MODELS_TO_CHECK = [
    "purchase.order.line",
    "account.move.line",
    "stock.picking",
    "sale.order.line",
]


def main():
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        print("❌ Authentification échouée. Vérifiez URL / DB / login / mot de passe.")
        return
    print(f"✅ Authentifié, uid={uid}\n")

    models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

    for model in MODELS_TO_CHECK:
        print(f"\n{'='*60}\n📦 {model}\n{'='*60}")
        try:
            fields = models.execute_kw(
                DB, uid, PASSWORD, model, "fields_get",
                [], {"attributes": ["string", "type"]}
            )
            # On n'affiche que les champs "utiles" (pas les champs techniques internes)
            for fname, info in sorted(fields.items()):
                if not fname.startswith(("__", "message_", "activity_")):
                    print(f"  {fname:30s} ({info['type']:12s}) - {info['string']}")

            print(f"\n--- Exemple de 2 enregistrements réels ---")
            sample = models.execute_kw(
                DB, uid, PASSWORD, model, "search_read",
                [[]], {"limit": 2}
            )
            print(json.dumps(sample, indent=2, ensure_ascii=False, default=str))

        except Exception as e:
            print(f"⚠️ Erreur sur {model}: {e}")


if __name__ == "__main__":
    main()