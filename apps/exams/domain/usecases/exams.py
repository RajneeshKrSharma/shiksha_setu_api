from datetime import date
from uuid import UUID

from apps.accounts.domain.capabilities import CONDUCT_EXAMS, SCHEDULE_EXAMS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase
from apps.students.domain.repositories import ClassRepository
from apps.teachers.domain.repositories import AllotmentRepository

from ..entities import Exam, ExamType, PaperStatus
from ..repositories import ExamRepository, MarkRepository, PaperRepository
from ..services import ExamLine, ExamScope


class _ExamUseCase(UseCase):
    def __init__(self, exams: ExamRepository, papers: PaperRepository, scope: ExamScope,
                 authorizer: Authorizer):
        self._exams = exams
        self._papers = papers
        self._scope = scope
        self._authorizer = authorizer

    def _existing(self, exam_id: UUID) -> Exam:
        exam = self._exams.get(exam_id)
        if exam is None or not exam.is_active:
            raise NotFound("This exam was not found.")
        return exam

    def _ensure_free(self, exam: Exam) -> None:
        twin = self._exams.find_same(exam.class_id, exam.subject, exam.exam_type, exam.held_on)
        if twin is not None and twin.id != exam.id:
            message = "This exam is already scheduled for that class, subject and day."
            raise RuleViolation(message, errors={"held_on": [message]})


class ListExams(_ExamUseCase):
    """The Principal sees every exam; a teacher sees the exams of the classes and subjects
    they take."""

    def call(self, actor: UserAccount, *, class_id: UUID | None = None,
             exam_type: ExamType | None = None, from_date: date | None = None,
             to_date: date | None = None) -> list[ExamLine]:
        self._authorizer.require_any(actor, SCHEDULE_EXAMS, CONDUCT_EXAMS)
        exams = self._exams.list(class_id=class_id, exam_type=exam_type, from_date=from_date,
                                 to_date=to_date)
        if not self._scope.sees_all(actor):
            held = self._scope.held_by(actor)
            exams = [e for e in exams if (e.class_id, e.subject.lower()) in held]
        return [self._scope.line(exam, self._papers) for exam in exams]


class ScheduleExam(_ExamUseCase):
    """The Principal fixes an exam. The class and subject must already have a teacher,
    who will conduct it."""

    def __init__(self, exams: ExamRepository, papers: PaperRepository, scope: ExamScope,
                 authorizer: Authorizer, classes: ClassRepository,
                 allotments: AllotmentRepository, audit: AuditLogger):
        super().__init__(exams, papers, scope, authorizer)
        self._classes = classes
        self._allotments = allotments
        self._audit = audit

    def call(self, actor: UserAccount, *, exam_type: ExamType, class_id: UUID, subject: str,
             held_on: date, max_marks: int) -> ExamLine:
        self._authorizer.require(actor, SCHEDULE_EXAMS)
        school_class = self._classes.get(class_id)
        if school_class is None or not school_class.is_active:
            raise RuleViolation("This class does not exist.",
                                errors={"class_id": ["Choose an existing class."]})
        holder = self._allotments.find_active(class_id, subject.strip())
        if holder is None:
            message = f"No teacher takes {subject.strip() or 'this subject'} in {school_class.name}. Allot one first."
            raise RuleViolation(message, errors={"subject": [message]})

        exam = Exam.schedule(exam_type=exam_type, class_id=class_id, subject=holder.subject,
                             held_on=held_on, max_marks=max_marks)
        self._ensure_free(exam)
        saved = self._exams.add(exam)
        self._audit.record(actor.id, "exam_scheduled", f"class:{class_id}", {
            "class": school_class.name, "subject": saved.subject, "type": exam_type.value,
            "on": held_on.isoformat(),
        })
        return self._scope.line(saved, self._papers)


class UpdateExam(_ExamUseCase):
    """Moves an exam or changes its type or total. The total cannot change once marks are
    entered or the paper has been sent."""

    ALLOWED = {"exam_type", "held_on", "max_marks"}

    def __init__(self, exams: ExamRepository, papers: PaperRepository, scope: ExamScope,
                 authorizer: Authorizer, marks: MarkRepository, audit: AuditLogger):
        super().__init__(exams, papers, scope, authorizer)
        self._marks = marks
        self._audit = audit

    def call(self, actor: UserAccount, exam_id: UUID, **changes) -> ExamLine:
        self._authorizer.require(actor, SCHEDULE_EXAMS)
        if not changes or not set(changes) <= self.ALLOWED:
            raise RuleViolation("Nothing to change.")
        exam = self._existing(exam_id)
        new_max = changes.get("max_marks", exam.max_marks)
        if new_max != exam.max_marks:
            if self._marks.count_for_exam(exam_id):
                raise RuleViolation("Marks are already entered, so the total cannot change.",
                                    errors={"max_marks": ["Marks already entered."]})
            paper = self._papers.for_exam(exam_id)
            if paper and paper.status in (PaperStatus.SENT, PaperStatus.APPROVED):
                raise RuleViolation("The paper is already sent, so the total cannot change.",
                                    errors={"max_marks": ["Paper already sent."]})
        exam.change(exam_type=changes.get("exam_type", exam.exam_type),
                    held_on=changes.get("held_on", exam.held_on), max_marks=new_max)
        self._ensure_free(exam)
        saved = self._exams.update(exam)
        self._audit.record(actor.id, "exam_updated", f"exam:{saved.id}", {
            "type": saved.exam_type.value, "on": saved.held_on.isoformat(), "max": saved.max_marks,
        })
        return self._scope.line(saved, self._papers)


class CancelExam(_ExamUseCase):
    """Cancelling hides the exam. An exam with marks cannot be cancelled."""

    def __init__(self, exams: ExamRepository, papers: PaperRepository, scope: ExamScope,
                 authorizer: Authorizer, marks: MarkRepository, audit: AuditLogger):
        super().__init__(exams, papers, scope, authorizer)
        self._marks = marks
        self._audit = audit

    def call(self, actor: UserAccount, exam_id: UUID) -> None:
        self._authorizer.require(actor, SCHEDULE_EXAMS)
        exam = self._existing(exam_id)
        if self._marks.count_for_exam(exam_id):
            raise RuleViolation("Marks are already entered, so this exam cannot be cancelled.")
        exam.cancel()
        self._exams.update(exam)
        self._audit.record(actor.id, "exam_cancelled", f"exam:{exam_id}", {
            "subject": exam.subject, "on": exam.held_on.isoformat(),
        })
