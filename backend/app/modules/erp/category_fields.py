"""
app/modules/erp/category_fields.py

Configuration ERP par categorie metier, alignee sur les memes categories
et les memes noms de champs cibles que app/modules/ocr/category_fields.py.

Objectif : qu'une donnee "Energie" venant d'Odoo et une donnee "Energie"
venant de l'OCR atterrissent dans le referentiel avec exactement les
memes cles de champs (ex: "Montant HT", "Fournisseur"), afin que le
dashboard/les indicateurs ne fassent aucune distinction de source.

Structure par categorie :
    odoo_model   -> modele Odoo interroge en priorite
    domain_extra -> filtre Odoo optionnel (ex: ne garder que les factures fournisseurs)
    field_map    -> { champ_source_odoo: champ_cible_referentiel }

Les champs cibles doivent correspondre a ceux de CATEGORY_FIELDS (ocr).
"""

CATEGORY_ERP_CONFIG: dict[str, dict] = {

    "Achats": {
        "odoo_model": "purchase.order.line",
        "domain_extra": [],
        "field_map": {
            "order_id": "N° facture",
            "date_planned": "Date de facturation",
            "product_id": "Description des articles",
            "product_qty": "Quantité",
            "product_uom": "Unité",
            "price_unit": "Prix unitaire HT",
            "price_subtotal": "Total HT",
            "price_tax": "Total TVA",
            "price_total": "Total TTC",
            "partner_id": "Fournisseur",
        },
    },

    "Comptabilité": {
        "odoo_model": "account.move.line",
        "domain_extra": [["move_id.move_type", "=", "in_invoice"]],
        "field_map": {
            "move_name": "N° facture",
            "date": "Date de facturation",
            "date_maturity": "Date d'échéance",
            "partner_id": "Fournisseur",
            "price_subtotal": "Montant HT",
            "price_total": "Montant TTC",
            "currency_id": "Devise",
        },
    },

    "Énergie": {
        "odoo_model": "account.move.line",
        "domain_extra": [["product_id.categ_id.name", "ilike", "energie"]],
        "field_map": {
            "move_name": "Référence",
            "date": "Période de facturation (début)",
            "date_maturity": "Date limite de paiement",
            "quantity": "Consommation (kWh)",
            "price_unit": "Prix unitaire (P.U.)",
            "price_subtotal": "Montant HT",
            "price_total": "Montant total",
            "partner_id": "Fournisseur",
        },
    },

    "Eau": {
        "odoo_model": "account.move.line",
        "domain_extra": [["product_id.categ_id.name", "ilike", "eau"]],
        "field_map": {
            "move_name": "Référence",
            "date": "Période de facturation (début)",
            "quantity": "Consommation (m³)",
            "price_unit": "Prix unitaire (P.U.)",
            "price_subtotal": "Montant HT",
            "price_total": "Montant total",
            "partner_id": "Fournisseur",
        },
    },

    "Déchets": {
        "odoo_model": "stock.picking",
        "domain_extra": [["picking_type_id.name", "ilike", "dechet"]],
        "field_map": {
            "name": "N° bordereau",
            "scheduled_date": "Date",
            "partner_id": "Collecteur",
            "origin": "Type de déchet",
        },
    },

    "Transport": {
        "odoo_model": "stock.picking",
        "domain_extra": [],
        "field_map": {
            "name": "N° expédition",
            "scheduled_date": "Date",
            "partner_id": "Transporteur",
            "origin": "Origine",
        },
    },

    "Stocks": {
        "odoo_model": "stock.quant",
        "domain_extra": [],
        "field_map": {
            "product_id": "Référence article",
            "quantity": "Inventaire",
            "location_id": "Emplacement / Entrepôt",
        },
    },

    "Immobilisations": {
        "odoo_model": "account.asset",
        "domain_extra": [],
        "field_map": {
            "name": "Nom actif",
            "acquisition_date": "Date d'acquisition",
            "original_value": "Valeur d'achat",
            "method_number": "Durée d'amortissement",
        },
    },

"Ventes": {
    "odoo_model": "sale.order.line",
    "domain_extra": [],
    "field_map": {
        "order_id": "N° facture",
        "product_id": "Produit vendu",
        "product_uom_qty": "Quantité vendue",
        "price_unit": "Prix unitaire",
        "price_total": "Chiffre d'affaires",
    },
},
"Maintenance": {
    "odoo_model": "maintenance.request",
    "domain_extra": [],
    "field_map": {
        "name": "Intervention",
        "equipment_id": "Équipement",
        "maintenance_team_id": "Équipe",
        "maintenance_type": "Type de maintenance",
        "request_date": "Date de la demande",
        "schedule_date": "Date planifiée",
        "close_date": "Date de clôture",
        "duration": "Durée (h)",
        "stage_id": "Statut",
    },
},
}




def available_categories() -> list[str]:
    """Categories pour lesquelles un connecteur ERP est configure."""
    return list(CATEGORY_ERP_CONFIG.keys())
def config_for(category: str) -> dict | None:
    """Retourne la config ERP pour une categorie, ou None."""
    return CATEGORY_ERP_CONFIG.get(category)