"""
app/modules/ocr/category_fields.py

Champs specifiques par categorie - version enrichie, alignee sur la
structure reelle des factures/documents (numero, dates, lignes de detail,
taxes, coordonnees bancaires...), pas seulement montant + fournisseur.

Source de verite unique : toute evolution des champs se fait ici.
"""

CATEGORY_FIELDS: dict[str, list[str]] = {

    "Achats": [
        "N° facture", "Date de facturation", "Date d'échéance", "Référence",
        "Fournisseur", "Adresse fournisseur", "Client / Destinataire",
        "Bon de commande", "Description des articles", "Quantité", "Unité",
        "Prix unitaire HT", "% TVA", "Total HT", "Total TVA", "Total TTC",
        "Remise", "Mode de paiement", "IBAN", "Banque",
    ],

    "Produits": [
        "Référence produit", "Nomenclature (BOM)", "Description produit",
        "Poids", "Unité", "Quantité", "Fournisseur / Fabricant", "Date",
    ],

    "Stocks": [
        "Référence article", "Entrées", "Sorties", "Inventaire", "Pertes",
        "Emplacement / Entrepôt", "Date",
    ],

    "Production": [
        "Ordre de fabrication", "Ligne de production", "Quantité produite",
        "Heures machine", "Opérateur", "Date",
    ],

    "Maintenance": [
        "Intervention", "Équipement", "Pièce remplacée", "Technicien",
        "Date intervention", "Durée", "Coût",
    ],

    "Transport": [
        "N° expédition", "Destination", "Origine", "Transporteur",
        "Distance (km)", "Poids / Volume", "Mode de transport", "Date",
    ],

    "Ventes": [
        "N° facture", "Client", "Pays", "Produit vendu", "Quantité vendue",
        "Prix unitaire", "Chiffre d'affaires", "Date",
    ],

    "RH": [
        "Nombre d'employés", "Site", "Type de déplacement",
        "Déplacements professionnels", "Trajets domicile-travail", "Date",
    ],

    "Comptabilité": [
        "N° facture", "Date de facturation", "Date d'échéance", "Référence",
        "Centre de coût", "Fournisseur", "Montant HT", "% TVA",
        "Montant TVA", "Montant TTC", "Devise", "Mode de paiement",
    ],

    "Immobilisations": [
        "Nom actif", "Type d'actif", "Numéro de série", "Fournisseur",
        "Date d'acquisition", "Valeur d'achat", "Durée d'amortissement",
    ],

    "Énergie": [
        "Référence", "N° dépannage / compteur", "District",
        "Période de facturation (début)", "Période de facturation (fin)",
        "Ancien index", "Nouvel index", "Consommation (kWh)",
        "Puissance / Débit", "Prix unitaire (P.U.)", "Montant HT",
        "Total Électricité", "Total Gaz", "TVA", "Contribution CL",
        "Contribution RTT", "FTE", "Total Taxes", "Montant total",
        "Arriérés", "Paiements précédents", "Montant à payer",
        "Date limite de paiement", "Fournisseur",
    ],

    "Eau": [
        "Référence", "District", "Période de facturation (début)",
        "Période de facturation (fin)", "Ancien index", "Nouvel index",
        "Consommation (m³)", "Prix unitaire (P.U.)", "Montant HT", "TVA",
        "Montant total", "Date limite de paiement", "Fournisseur",
    ],

    "Déchets": [
        "N° bordereau", "Type de déchet", "Quantité (t)",
        "Mode de traitement", "Collecteur", "Transporteur",
        "Site de traitement", "Date",
    ],

    "Carburant": [
        "Type de carburant", "Volume (L)", "Véhicule / équipement",
        "Prix unitaire", "Montant total", "Fournisseur", "Période",
    ],
}


def fields_for(category: str) -> list[str]:
    return CATEGORY_FIELDS.get(category, [])
