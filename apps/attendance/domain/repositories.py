from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from apps.core.domain.repository import Repository

from .entities import StudentMark, StudentStatus, WorkAttendance


class StudentMarkRepository(ABC):
    @abstractmethod
    def save_many(self, marks: list[StudentMark]) -> None:
        """Adds each mark, or replaces the student's mark for that day."""

    @abstractmethod
    def for_class_day(self, class_id: UUID, day: date) -> dict[UUID, StudentMark]:
        """By student id."""

    @abstractmethod
    def daily_counts(self, from_date: date, to_date: date, class_id: UUID | None = None
                     ) -> dict[date, dict[StudentStatus, int]]:
        """Marks per status for each day, for one class or the whole school."""

    @abstractmethod
    def tally(self, class_id: UUID, from_date: date, to_date: date
              ) -> dict[UUID, dict[StudentStatus, int]]:
        """Days marked present, late and absent, by student id."""


class WorkAttendanceRepository(Repository[WorkAttendance]):
    @abstractmethod
    def find(self, person_id: UUID, day: date) -> WorkAttendance | None: ...

    @abstractmethod
    def on_day(self, day: date) -> dict[UUID, WorkAttendance]:
        """By person id."""

    @abstractmethod
    def list(self, *, person_id: UUID | None = None, from_date: date | None = None,
             to_date: date | None = None) -> list[WorkAttendance]:
        """Newest day first."""
