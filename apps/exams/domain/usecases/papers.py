from uuid import UUID

from apps.accounts.domain.capabilities import PREPARE_QUESTIONS, SCHEDULE_EXAMS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.clock import Clock
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import Exam, Paper, PaperStatus, Question
from ..repositories import ExamRepository, PaperRepository, QuestionRepository, UnitRepository
from ..services import ExamScope


class _PaperUseCase(UseCase):
    def __init__(self, exams: ExamRepository, papers: PaperRepository, scope: ExamScope,
                 authorizer: Authorizer):
        self._exams = exams
        self._papers = papers
        self._scope = scope
        self._authorizer = authorizer

    def _exam(self, exam_id: UUID) -> Exam:
        exam = self._exams.get(exam_id)
        if exam is None or not exam.is_active:
            raise NotFound("This exam was not found.")
        return exam

    def _paper(self, exam_id: UUID) -> Paper:
        paper = self._papers.for_exam(exam_id)
        if paper is None:
            raise NotFound("There is no paper for this exam yet.")
        return paper


class GetPaper(_PaperUseCase):
    def call(self, actor: UserAccount, exam_id: UUID) -> Paper:
        self._authorizer.require_any(actor, PREPARE_QUESTIONS, SCHEDULE_EXAMS)
        exam = self._exam(exam_id)
        self._scope.require_conductor(actor, exam)
        return self._paper(exam_id)


class ListPapers(UseCase):
    """For the Principal: the papers waiting to be looked at, or any status."""

    def __init__(self, papers: PaperRepository, authorizer: Authorizer):
        self._papers = papers
        self._authorizer = authorizer

    def call(self, actor: UserAccount, *, status: PaperStatus | None = None) -> list[Paper]:
        self._authorizer.require(actor, SCHEDULE_EXAMS)
        return self._papers.list(status=status)


class ComposePaper(_PaperUseCase):
    """The teacher of the exam's class and subject picks questions from their own bank.
    Choosing again replaces the list; a rejected paper becomes a draft again."""

    def __init__(self, exams: ExamRepository, papers: PaperRepository, scope: ExamScope,
                 authorizer: Authorizer, units: UnitRepository, questions: QuestionRepository):
        super().__init__(exams, papers, scope, authorizer)
        self._units = units
        self._questions = questions

    def call(self, actor: UserAccount, exam_id: UUID, *, question_ids: list[UUID]) -> Paper:
        self._authorizer.require(actor, PREPARE_QUESTIONS)
        exam = self._exam(exam_id)
        self._scope.require_holder(actor, exam)
        if len(set(question_ids)) != len(question_ids):
            raise RuleViolation("A question is in the list twice.",
                                errors={"question_ids": ["Each question once."]})
        found = self._questions.get_many(question_ids)
        questions = [self._usable(actor, exam, found.get(qid)) for qid in question_ids]

        paper = self._papers.for_exam(exam_id) or Paper(exam_id=exam_id, prepared_by_id=actor.id)
        paper.compose(questions)
        return self._papers.update(paper) if paper.id else self._papers.add(paper)

    def _usable(self, actor: UserAccount, exam: Exam, question: Question | None) -> Question:
        unit = self._units.get(question.unit_id) if question else None
        if question is None or unit is None or not unit.is_active:
            raise RuleViolation("A question was not found.",
                                errors={"question_ids": ["Choose questions from your bank."]})
        if (unit.teacher_id != actor.id or unit.class_id != exam.class_id
                or unit.subject.lower() != exam.subject.lower()):
            raise RuleViolation(
                "A question is not from your bank for this class and subject.",
                errors={"question_ids": ["Choose questions of this class and subject."]},
            )
        return question


class SendPaper(_PaperUseCase):
    """Sends the paper to the Principal. It must add up to the exam's total marks."""

    def __init__(self, exams: ExamRepository, papers: PaperRepository, scope: ExamScope,
                 authorizer: Authorizer, audit: AuditLogger):
        super().__init__(exams, papers, scope, authorizer)
        self._audit = audit

    def call(self, actor: UserAccount, exam_id: UUID) -> Paper:
        self._authorizer.require(actor, PREPARE_QUESTIONS)
        exam = self._exam(exam_id)
        self._scope.require_holder(actor, exam)
        paper = self._paper(exam_id)
        paper.send(exam_max_marks=exam.max_marks)
        saved = self._papers.update(paper)
        self._audit.record(actor.id, "paper_sent", f"exam:{exam_id}", {
            "subject": exam.subject, "marks": saved.total_marks,
        })
        return saved


class _PaperDecision(_PaperUseCase):
    def __init__(self, exams: ExamRepository, papers: PaperRepository, scope: ExamScope,
                 authorizer: Authorizer, audit: AuditLogger, clock: Clock):
        super().__init__(exams, papers, scope, authorizer)
        self._audit = audit
        self._clock = clock


class ApprovePaper(_PaperDecision):
    def call(self, actor: UserAccount, exam_id: UUID) -> Paper:
        self._authorizer.require(actor, SCHEDULE_EXAMS)
        exam = self._exam(exam_id)
        paper = self._paper(exam_id)
        paper.approve(by_id=actor.id, on=self._clock.today())
        saved = self._papers.update(paper)
        self._audit.record(actor.id, "paper_approved", f"exam:{exam_id}", {"subject": exam.subject})
        return saved


class RejectPaper(_PaperDecision):
    def call(self, actor: UserAccount, exam_id: UUID, *, reason: str) -> Paper:
        self._authorizer.require(actor, SCHEDULE_EXAMS)
        exam = self._exam(exam_id)
        paper = self._paper(exam_id)
        paper.reject(by_id=actor.id, on=self._clock.today(), reason=reason)
        saved = self._papers.update(paper)
        self._audit.record(actor.id, "paper_rejected", f"exam:{exam_id}", {
            "subject": exam.subject, "reason": saved.decision_note,
        })
        return saved
