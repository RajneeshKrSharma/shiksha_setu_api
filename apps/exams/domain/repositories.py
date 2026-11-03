from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from apps.core.domain.repository import Repository

from .entities import (
    Exam,
    ExamMark,
    ExamType,
    Paper,
    PaperStatus,
    Question,
    QuestionUnit,
)


class ExamRepository(Repository[Exam]):
    @abstractmethod
    def list(self, *, class_ids: frozenset[UUID] | None = None, class_id: UUID | None = None,
             exam_type: ExamType | None = None, from_date: date | None = None,
             to_date: date | None = None) -> list[Exam]:
        """Active exams, soonest first. `class_ids` narrows to those classes."""

    @abstractmethod
    def find_same(self, class_id: UUID, subject: str, exam_type: ExamType,
                  held_on: date) -> Exam | None:
        """An active exam of the same class, subject, type and day (subject ignoring case)."""


class UnitRepository(Repository[QuestionUnit]):
    @abstractmethod
    def list(self, *, teacher_id: UUID | None = None, class_id: UUID | None = None,
             subject: str | None = None) -> list[QuestionUnit]:
        """Active units, by class then name."""

    @abstractmethod
    def find_same(self, teacher_id: UUID, class_id: UUID, subject: str,
                  name: str) -> QuestionUnit | None:
        """An active unit with the same teacher, class, subject and name (ignoring case)."""


class QuestionRepository(Repository[Question]):
    @abstractmethod
    def list(self, unit_id: UUID) -> list[Question]:
        """Active questions of a unit, oldest first."""

    @abstractmethod
    def get_many(self, ids: list[UUID]) -> dict[UUID, Question]:
        """Active questions by id; ids that are missing or removed are left out."""


class PaperRepository(Repository[Paper]):
    @abstractmethod
    def for_exam(self, exam_id: UUID) -> Paper | None: ...

    @abstractmethod
    def list(self, *, status: PaperStatus | None = None) -> list[Paper]:
        """Newest first."""


class MarkRepository(ABC):
    @abstractmethod
    def save_many(self, marks: list[ExamMark]) -> None:
        """Adds each mark, or replaces the student's mark in that exam."""

    @abstractmethod
    def for_exam(self, exam_id: UUID) -> dict[UUID, ExamMark]:
        """By student id."""

    @abstractmethod
    def for_student(self, student_id: UUID) -> dict[UUID, ExamMark]:
        """By exam id."""

    @abstractmethod
    def count_for_exam(self, exam_id: UUID) -> int: ...
