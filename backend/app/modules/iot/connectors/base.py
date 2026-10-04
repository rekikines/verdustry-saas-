"""
Interface commune des connecteurs IoT — app/modules/iot/connectors/base.py

Même logique que vos connecteurs ERP (base.py, odoo.py) : chaque protocole
(Modbus, MQTT, LoRaWAN, simulateur) implémente cette classe abstraite.
"""

from abc import ABC, abstractmethod
from app.modules.iot.schemas import ReadingIn


class BaseIoTConnector(ABC):
    """Un connecteur sait se connecter à une source physique/logique de
    données IoT et produire des ReadingIn normalisés, quel que soit le
    protocole sous-jacent."""

    @abstractmethod
    def connect(self) -> None:
        """Établit la connexion (socket Modbus, souscription MQTT, etc.)."""
        raise NotImplementedError

    @abstractmethod
    def fetch_readings(self) -> list[ReadingIn]:
        """Récupère un lot de mesures brutes depuis la source."""
        raise NotImplementedError

    def normalize(self, raw: dict) -> ReadingIn:
        """Point d'extension pour un mapping spécifique si le payload brut
        ne correspond pas directement au schéma ReadingIn."""
        return ReadingIn(**raw)
