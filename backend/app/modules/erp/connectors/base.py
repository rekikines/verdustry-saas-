# app/modules/erp/connectors/base.py
from abc import ABC, abstractmethod


class ERPConnector(ABC):
    @abstractmethod
    def test_connection(self) -> bool:
        ...

    @abstractmethod
    def extract(self, model: str, domain: list, fields: list, limit: int = 500) -> list[dict]:
        ...