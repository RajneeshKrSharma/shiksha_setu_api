from abc import ABC, abstractmethod

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class FieldEncryptor(ABC):
    """For the few fields the school decides are sensitive. Not used until one is chosen."""

    @abstractmethod
    def encrypt(self, plain: str) -> str: ...

    @abstractmethod
    def decrypt(self, token: str) -> str: ...


class FernetFieldEncryptor(FieldEncryptor):
    """The key comes from FIELD_ENCRYPTION_KEY, never from the database."""

    def __init__(self, key: str | None = None):
        key = key or getattr(settings, "FIELD_ENCRYPTION_KEY", "")
        if not key:
            raise ImproperlyConfigured("Set FIELD_ENCRYPTION_KEY to encrypt fields.")
        self._fernet = Fernet(key.encode())

    def encrypt(self, plain: str) -> str:
        return self._fernet.encrypt(plain.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()
