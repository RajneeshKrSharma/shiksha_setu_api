from dataclasses import dataclass
from uuid import UUID

from apps.accounts.domain.capabilities import CONDUCT_EXAMS, SCHEDULE_EXAMS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.clock import Clock
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase
from apps.students.domain.repositories import StudentRepository

from ..entities import ExamMark, ExamResults
from ..repositories import ExamRepository, MarkRepository
from ..services import ExamScope, ResultBuilder


@dataclass(frozen=True)
class MarkEntry:
    student_id: UUID
    marks: int | None = None
    absent: bool = False


class EnterMarks(UseCase):
    """The teacher of the exam's class and subject (or the Principal) enters marks once
    the exam day has come. A student entered again gets the new marks; students left out
    stay as they were."""

    def __init__(self, exams: ExamRepository, marks: MarkRepository, students: StudentRepository,
                 results: ResultBuilder, scope: ExamScope, authorizer: Authorizer,
                 audit: AuditLogger, clock: Clock):
        self._exams = exams
        self._marks = marks
        self._students = students
        self._results = results
        self._scope = scope
        self._authorizer = authorizer
        self._audit = audit
        self._clock = clock

    def call(self, actor: UserAccount, exam_id: UUID, *, entries: list[MarkEntry]) -> ExamResults:
        self._authorizer.require_any(actor, CONDUCT_EXAMS, SCHEDULE_EXAMS)
        exam = self._exams.get(exam_id)
        if exam is None or not exam.is_active:
            raise NotFound("This exam was not found.")
        self._scope.require_conductor(actor, exam)
        if not exam.has_been_held(self._clock.today()):
            raise RuleViolation("Marks can be entered once the day of the exam has come.",
                                errors={"marks": ["The exam is not held yet."]})
        if not entries:
            raise RuleViolation("Enter marks for at least one student.",
                                errors={"marks": ["Required."]})

        in_class = {s.id for s in self._students.list(class_id=exam.class_id, active=True)}
        seen: set[UUID] = set()
        to_save = []
        for entry in entries:
            if entry.student_id not in in_class:
                raise RuleViolation("A student in the list is not in this class.",
                                    errors={"marks": ["Not a student of this class."]})
            if entry.student_id in seen:
                raise RuleViolation("A student is in the list twice.",
                                    errors={"marks": ["Each student once."]})
            seen.add(entry.student_id)
            to_save.append(ExamMark.enter(
                exam=exam, student_id=entry.student_id, marks=entry.marks, absent=entry.absent,
                entered_by_id=actor.id,
            ))
        self._marks.save_many(to_save)
        self._audit.record(actor.id, "marks_entered", f"exam:{exam_id}", {
            "subject": exam.subject, "students": len(to_save),
        })
        return self._results.for_exam(exam)
