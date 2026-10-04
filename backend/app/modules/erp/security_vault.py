# app/modules/erp/security_vault.py
from cryptography.fernet import Fernet
from app.core.config import settings

_fernet = Fernet(settings.encryption_key.encode())  

def encrypt_value(plain: str) -> str:
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_value(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()