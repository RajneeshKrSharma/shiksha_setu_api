from __future__ import annotations

from abc import abstractmethod
from datetime import date
from uuid import UUID

from apps.core.domain.repository import Repository

from .entities import Request, RequestKind, RequestStatus


class RequestRepository(Repository[Request]):
    @abstractmethod
    def list(self, *, kind: RequestKind | None = None, status: RequestStatus | None = None,
             requester_id: UUID | None = None) -> list[Request]:
        """Newest first."""

    @abstractmethod
    def has_leave_between(self, requester_id: UUID, starts_on: date, ends_on: date) -> bool:
        """Whether the person already has a pending or approved leave touching these days."""

    @abstractmethod
    def people_on_leave(self, day: date) -> frozenset[UUID]:
        """Everyone with an approved leave covering the day."""
