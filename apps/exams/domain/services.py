from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from apps.accounts.domain.capabilities import MANAGE_QUESTION_BANK, SCHEDULE_EXAMS, VIEW_RESULTS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.errors import Forbidden
from apps.core.domain.money import ZERO
from apps.students.domain.entities import Student
from apps.students.domain.repositories import StudentRepository
from apps.teachers.domain.entities import Allotment
from apps.teachers.domain.repositories import AllotmentRepository

from .entities import (
    Exam,
    ExamResults,
    PaperStatus,
    ResultLine,
    StudentExamLine,
    StudentResults,
    percent,
)
from .repositories import MarkRepository, PaperRepository


@dataclass(frozen=True)
class ExamLine:
    """An exam with the teacher who takes it and the state of its paper."""

    exam: Exam
    teacher_id: UUID | None
    teacher_name: str
    paper_status: PaperStatus | None


class ExamScope:
    """Who may do what with an exam. The teacher holding the exam's class and subject
    conducts it; whoever schedules exams (the Principal) may act on any exam."""

    def __init__(self, authorizer: Authorizer, allotments: AllotmentRepository):
        self._authorizer = authorizer
        self._allotments = allotments

    def holder_of(self, exam: Exam) -> Allotment | None:
        return self._allotments.find_active(exam.class_id, exam.subject)

    def is_holder(self, actor: UserAccount, exam: Exam) -> bool:
        holder = self.holder_of(exam)
        return holder is not None and holder.teacher_id == actor.id

    def sees_all(self, actor: UserAccount) -> bool:
        held = self._authorizer.capabilities_of(actor)
        return SCHEDULE_EXAMS in held or VIEW_RESULTS in held

    def may_conduct(self, actor: UserAccount, exam: Exam) -> bool:
        return self._authorizer.can(actor, SCHEDULE_EXAMS) or self.is_holder(actor, exam)

    def require_conductor(self, actor: UserAccount, exam: Exam) -> None:
        if not self.may_conduct(actor, exam):
            raise Forbidden("This exam is not yours to conduct.")

    def require_holder(self, actor: UserAccount, exam: Exam) -> None:
        if not self.is_holder(actor, exam):
            raise Forbidden("Only the teacher of this class and subject can do this.")

    def held_by(self, actor: UserAccount) -> frozenset[tuple[UUID, str]]:
        """The (class, subject) pairs the actor takes, subject in lower case."""
        return frozenset(
            (a.class_id, a.subject.lower()) for a in self._allotments.list(teacher_id=actor.id)
        )

    def line(self, exam: Exam, papers: PaperRepository) -> ExamLine:
        holder = self.holder_of(exam)
        paper = papers.for_exam(exam.id)
        return ExamLine(
            exam=exam,
            teacher_id=holder.teacher_id if holder else None,
            teacher_name=holder.teacher_name if holder else "",
            paper_status=paper.status if paper else None,
        )


class ResultBuilder:
    """Turns marks into results: marks, percentage, and how the class did."""

    def __init__(self, students: StudentRepository, marks: MarkRepository):
        self._students = students
        self._marks = marks

    def for_exam(self, exam: Exam) -> ExamResults:
        marks = self._marks.for_exam(exam.id)
        lines = []
        for student in self._students.list(class_id=exam.class_id, active=True):
            mark = marks.get(student.id)
            got = mark is not None and not mark.absent
            lines.append(ResultLine(student, mark, percent(mark.marks, exam.max_marks) if got else None))
        scored = [line.mark.marks for line in lines if line.mark and not line.mark.absent]
        average = (
            (Decimal(sum(scored)) / len(scored)).quantize(ZERO, rounding=ROUND_HALF_UP)
            if scored else None
        )
        return ExamResults(
            exam=exam, lines=lines, entered=len(scored),
            absent=sum(1 for line in lines if line.mark and line.mark.absent),
            average=average, highest=max(scored, default=None), lowest=min(scored, default=None),
        )

    def for_student(self, student: Student, exams: list[Exam]) -> StudentResults:
        marks = self._marks.for_student(student.id)
        lines = []
        for exam in exams:
            mark = marks.get(exam.id)
            got = mark is not None and not mark.absent
            lines.append(StudentExamLine(exam, mark, percent(mark.marks, exam.max_marks) if got else None))
        scored = [line for line in lines if line.mark and not line.mark.absent]
        obtained = sum(line.mark.marks for line in scored)
        out_of = sum(line.exam.max_marks for line in scored)
        return StudentResults(
            student=student, lines=lines, total_obtained=obtained, total_out_of=out_of,
            percentage=percent(obtained, out_of) if out_of else None,
        )


class BankScope:
    """Question banks belong to the teacher who made them. Whoever schedules exams or sees
    results can read every bank; only the owner changes one."""

    def __init__(self, authorizer: Authorizer):
        self._authorizer = authorizer

    def sees_all(self, actor: UserAccount) -> bool:
        held = self._authorizer.capabilities_of(actor)
        return SCHEDULE_EXAMS in held or VIEW_RESULTS in held

    def narrow(self, actor: UserAccount, teacher_id: UUID | None) -> UUID | None:
        """The teacher whose bank to list: anyone asked for if the actor sees all banks,
        otherwise only the actor's own."""
        if self.sees_all(actor):
            return teacher_id
        self._authorizer.require(actor, MANAGE_QUESTION_BANK)
        if teacher_id not in (None, actor.id):
            raise Forbidden()
        return actor.id
