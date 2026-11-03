from abc import abstractmethod
from datetime import date
from uuid import UUID

from apps.core.domain.repository import MemberRepository, Repository

from .entities import Allotment, Lesson, Teacher


class TeacherRepository(MemberRepository[Teacher]):
    """Teachers are sign-in accounts with the teacher role."""

    @abstractmethod
    def add(self, teacher: Teacher, password: str | None = None) -> Teacher: ...


class AllotmentRepository(Repository[Allotment]):
    @abstractmethod
    def list(self, *, teacher_id: UUID | None = None, class_id: UUID | None = None,
             active: bool = True, teacher_active: bool | None = None) -> list[Allotment]:
        """By class, then subject. `teacher_active` narrows to teachers who can still sign in."""

    @abstractmethod
    def find_active(self, class_id: UUID, subject: str) -> Allotment | None:
        """The active allotment of this class and subject, ignoring letter case."""


class LessonRepository(Repository[Lesson]):
    @abstractmethod
    def find(self, allotment_id: UUID, taught_on: date) -> Lesson | None: ...

    @abstractmethod
    def list(self, *, teacher_id: UUID | None = None, class_id: UUID | None = None,
             from_date: date | None = None, to_date: date | None = None) -> list[Lesson]:
        """Newest day first."""

    @abstractmethod
    def on_day(self, day: date) -> dict[UUID, Lesson]:
        """The lessons of one day, by allotment id."""
