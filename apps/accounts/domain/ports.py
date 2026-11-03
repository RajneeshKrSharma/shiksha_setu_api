"""What the accounts use cases need from the outside world."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .entities import UserAccount


@dataclass(frozen=True)
class TokenPair:
    access: str
    refresh: str


class PasswordPolicy(ABC):
    @abstractmethod
    def validate(self, password: str, account: UserAccount | None = None) -> None:
        """Raises RuleViolation when the password is too weak."""


class Authenticator(ABC):
    @abstractmethod
    def authenticate(self, email: str, password: str) -> UserAccount:
        """Raises Unauthenticated for a wrong email or password, Locked after too many tries."""


class TokenIssuer(ABC):
    @abstractmethod
    def issue(self, account: UserAccount) -> TokenPair: ...

    @abstractmethod
    def refresh(self, refresh_token: str) -> TokenPair:
        """Raises Unauthenticated when the token is bad or expired."""
