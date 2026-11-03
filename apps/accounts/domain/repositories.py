from abc import abstractmethod
from uuid import UUID

from apps.core.domain.repository import Repository

from .entities import PermissionGrant, Role, UserAccount


class UserRepository(Repository[UserAccount]):
    @abstractmethod
    def get_by_email(self, email: str) -> UserAccount | None: ...

    @abstractmethod
    def add(self, account: UserAccount, password: str | None = None) -> UserAccount: ...

    @abstractmethod
    def has_role(self, role: Role) -> bool: ...

    @abstractmethod
    def check_password(self, user_id: UUID, password: str) -> bool: ...

    @abstractmethod
    def set_password(self, user_id: UUID, password: str) -> None: ...

    @abstractmethod
    def list(self, *, role: Role, query: str = "", active: bool | None = None) -> list[UserAccount]:
        """People with this role, by name."""


class GrantRepository(Repository[PermissionGrant]):
    @abstractmethod
    def list(self, *, user_id: UUID | None = None,
             active_only: bool = True) -> list[PermissionGrant]: ...

    @abstractmethod
    def find_active(self, user_id: UUID, capability: str) -> PermissionGrant | None: ...
