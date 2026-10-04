# app/modules/erp/connectors/odoo.py
import xmlrpc.client
from .base import ERPConnector


class OdooConnector(ERPConnector):
    """
    Connecteur en lecture seule strict : utilise uniquement search_read.
    Jamais de create / write / unlink — conforme à la contrainte
    'aucune écriture dans les systèmes sources' du cahier des charges.
    """

    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self._common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self._models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def test_connection(self) -> bool:
        try:
            self.uid = self._common.authenticate(self.db, self.username, self.password, {})
            return bool(self.uid)
        except Exception as e:
            raise ConnectionError(f"Échec d'authentification Odoo : {e}")

    def extract(self, model: str, domain: list, fields: list, limit: int = 500) -> list[dict]:
        if not self.uid:
            self.test_connection()
        try:
            return self._models.execute_kw(
                self.db, self.uid, self.password,
                model, "search_read",
                [domain], {"fields": fields, "limit": limit},
            )
        except Exception as e:
            raise RuntimeError(f"Erreur d'extraction Odoo sur {model} : {e}")