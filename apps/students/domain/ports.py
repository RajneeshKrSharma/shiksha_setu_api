from abc import ABC, abstractmethod
from uuid import UUID

from apps.accounts.domain.entities import UserAccount


class ClassAccess(ABC):
    """Which classes a person may look at. The teachers module answers this from its
    class allotments; students only asks."""

    @abstractmethod
    def visible_class_ids(self, actor: UserAccount) -> frozenset[UUID] | None:
        """None means every class."""
