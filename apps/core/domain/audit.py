from abc import ABC, abstractmethod
from uuid import UUID


class AuditLogger(ABC):
    """Remembers who did what, for approvals, payments, grants and deletes."""

    @abstractmethod
    def record(self, actor_id: UUID | None, action: str, target: str,
               details: dict | None = None) -> None: ...
