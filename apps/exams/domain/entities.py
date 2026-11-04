from dataclasses import dataclass, field
from datetime import date, time
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from uuid import UUID

from apps.core.domain.entity import Entity
from apps.core.domain.errors import RuleViolation
from apps.core.domain.money import ZERO
from apps.students.domain.entities import Student


def _invalid(field_name: str, message: str) -> RuleViolation:
    return RuleViolation(message, errors={field_name: [message]})


def percent(obtained: int | Decimal, out_of: int | Decimal) -> Decimal:
    return (Decimal(obtained) * 100 / Decimal(out_of)).quantize(ZERO, rounding=ROUND_HALF_UP)


# --------------------------------------------------------------- the exam
class ExamType(StrEnum):
    UNIT_TEST = "unit_test"
    MID_TERM = "mid_term"
    ANNUAL = "annual"


@dataclass(eq=False, kw_only=True)
class Exam(Entity):
    """One exam of one subject for one class on one day, out of a total. Marks are whole
    numbers."""

    MAX_MARKS_LIMIT = 1000

    exam_type: ExamType
    class_id: UUID
    subject: str
    held_on: date
    max_marks: int
    is_active: bool = True
    class_name: str = ""
    # When the paper starts and how long it runs; both optional.
    starts_at: time | None = None
    duration_minutes: int | None = None

    @classmethod
    def schedule(cls, *, exam_type: ExamType, class_id: UUID, subject: str, held_on: date,
                 max_marks: int, starts_at: time | None = None,
                 duration_minutes: int | None = None) -> "Exam":
        exam = cls(exam_type=exam_type, class_id=class_id, subject=subject, held_on=held_on,
                   max_marks=1)
        exam.change(exam_type=exam_type, held_on=held_on, max_marks=max_marks,
                    starts_at=starts_at, duration_minutes=duration_minutes)
        return exam

    def change(self, *, exam_type: ExamType, held_on: date, max_marks: int,
               starts_at: time | None = None, duration_minutes: int | None = None) -> None:
        if not 1 <= max_marks <= self.MAX_MARKS_LIMIT:
            raise _invalid("max_marks", f"Between 1 and {self.MAX_MARKS_LIMIT}.")
        if duration_minutes is not None and duration_minutes < 1:
            raise _invalid("duration_minutes", "Must be at least 1 minute.")
        self.exam_type, self.held_on, self.max_marks = exam_type, held_on, max_marks
        self.starts_at, self.duration_minutes = starts_at, duration_minutes

    def cancel(self) -> None:
        self.is_active = False

    def has_been_held(self, today: date) -> bool:
        return self.held_on <= today


# ------------------------------------------------- exam timetable settings
class SameDayRule(StrEnum):
    """What to do when a class would sit two papers on one day."""

    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass(eq=False, kw_only=True)
class ExamSettings:
    """How the Principal wants exam timetables made. One set for the whole school; every
    value can be changed, and the starting values stop nothing."""

    DEFAULT_TYPE_LABELS = {
        ExamType.UNIT_TEST: "Unit Test",
        ExamType.MID_TERM: "Half Yearly",
        ExamType.ANNUAL: "Annual",
    }

    default_max_marks: int = 50
    default_duration_minutes: int = 180
    default_start_time: time | None = None
    show_time: bool = True
    same_day_rule: SameDayRule = SameDayRule.WARN
    min_gap_days: int = 0
    off_weekdays: list[int] = field(default_factory=lambda: [6])  # Monday is 0, Sunday 6
    off_dates: list[date] = field(default_factory=list)
    type_labels: dict[ExamType, str] = field(
        default_factory=lambda: dict(ExamSettings.DEFAULT_TYPE_LABELS)
    )

    def change(self, *, default_max_marks: int, default_duration_minutes: int,
               default_start_time: time | None, show_time: bool, same_day_rule: SameDayRule,
               min_gap_days: int, off_weekdays: list[int], off_dates: list[date],
               type_labels: dict[ExamType, str]) -> None:
        if not 1 <= default_max_marks <= Exam.MAX_MARKS_LIMIT:
            raise _invalid("default_max_marks", f"Between 1 and {Exam.MAX_MARKS_LIMIT}.")
        if default_duration_minutes < 1:
            raise _invalid("default_duration_minutes", "Must be at least 1 minute.")
        if min_gap_days < 0:
            raise _invalid("min_gap_days", "Cannot be below 0.")
        if any(not 0 <= d <= 6 for d in off_weekdays):
            raise _invalid("off_weekdays", "Days are 0 (Monday) to 6 (Sunday).")
        labels = {}
        for exam_type in ExamType:
            label = (type_labels.get(exam_type) or "").strip()
            labels[exam_type] = label or self.DEFAULT_TYPE_LABELS[exam_type]
            if len(labels[exam_type]) > 40:
                raise _invalid("type_labels", "Names can be up to 40 letters.")
        self.default_max_marks = default_max_marks
        self.default_duration_minutes = default_duration_minutes
        self.default_start_time, self.show_time = default_start_time, show_time
        self.same_day_rule, self.min_gap_days = same_day_rule, min_gap_days
        self.off_weekdays = sorted(set(off_weekdays))
        self.off_dates = sorted(set(off_dates))
        self.type_labels = labels

    def is_off_day(self, day: date) -> bool:
        return day.weekday() in self.off_weekdays or day in self.off_dates


# ---------------------------------------------------------- question bank
class QuestionType(StrEnum):
    MCQ = "mcq"
    SHORT = "short"
    LONG = "long"


@dataclass(eq=False, kw_only=True)
class QuestionUnit(Entity):
    """A teacher's unit of a class and subject, such as "Unit 2: Fractions"."""

    NAME_MAX = 80

    teacher_id: UUID
    class_id: UUID
    subject: str
    name: str
    is_active: bool = True
    class_name: str = ""
    teacher_name: str = ""

    @classmethod
    def create(cls, *, teacher_id: UUID, class_id: UUID, subject: str, name: str) -> "QuestionUnit":
        unit = cls(teacher_id=teacher_id, class_id=class_id, subject=subject, name="-")
        unit.rename(name)
        return unit

    def rename(self, name: str) -> None:
        name = name.strip()
        if not name or len(name) > self.NAME_MAX:
            raise _invalid("name", f"Required, up to {self.NAME_MAX} characters.")
        self.name = name

    def remove(self) -> None:
        self.is_active = False


@dataclass(eq=False, kw_only=True)
class Question(Entity):
    TEXT_MAX = 1000
    MARKS_MAX = 100

    unit_id: UUID
    text: str
    marks: int
    question_type: QuestionType
    is_active: bool = True

    @classmethod
    def create(cls, *, unit_id: UUID, text: str, marks: int,
               question_type: QuestionType) -> "Question":
        question = cls(unit_id=unit_id, text="-", marks=1, question_type=question_type)
        question.change(text=text, marks=marks, question_type=question_type)
        return question

    def change(self, *, text: str, marks: int, question_type: QuestionType) -> None:
        text = text.strip()
        if not text or len(text) > self.TEXT_MAX:
            raise _invalid("text", f"Required, up to {self.TEXT_MAX} characters.")
        if not 1 <= marks <= self.MARKS_MAX:
            raise _invalid("marks", f"Between 1 and {self.MARKS_MAX}.")
        self.text, self.marks, self.question_type = text, marks, question_type

    def remove(self) -> None:
        self.is_active = False


# ------------------------------------------------------------------ paper
class PaperStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class PaperItem:
    """A question as it stands in the paper. Text and marks are copied, so changing the
    bank later never changes a paper."""

    position: int
    question_id: UUID | None
    text: str
    marks: int
    question_type: QuestionType


@dataclass(eq=False, kw_only=True)
class Paper(Entity):
    """The question paper of an exam, built from the teacher's bank and approved by the
    Principal. A draft or rejected paper can be changed; a sent one waits; an approved
    one is final."""

    REASON_MAX = 300

    exam_id: UUID
    prepared_by_id: UUID
    items: list[PaperItem] = field(default_factory=list)
    status: PaperStatus = PaperStatus.DRAFT
    decided_by_id: UUID | None = None
    decided_on: date | None = None
    decision_note: str = ""
    prepared_by_name: str = ""

    @property
    def total_marks(self) -> int:
        return sum(item.marks for item in self.items)

    def compose(self, questions: list[Question]) -> None:
        if self.status not in (PaperStatus.DRAFT, PaperStatus.REJECTED):
            raise RuleViolation(f"A {self.status.value} paper cannot be changed.")
        self.items = [
            PaperItem(i + 1, q.id, q.text, q.marks, q.question_type) for i, q in enumerate(questions)
        ]
        self.status = PaperStatus.DRAFT
        self.decided_by_id, self.decided_on, self.decision_note = None, None, ""

    def send(self, *, exam_max_marks: int) -> None:
        if self.status != PaperStatus.DRAFT:
            raise RuleViolation(f"A {self.status.value} paper cannot be sent.")
        if not self.items:
            raise _invalid("question_ids", "Add questions first.")
        if self.total_marks != exam_max_marks:
            message = (f"The questions add up to {self.total_marks} marks, "
                       f"but the exam is out of {exam_max_marks}.")
            raise _invalid("question_ids", message)
        self.status = PaperStatus.SENT

    def approve(self, *, by_id: UUID, on: date) -> None:
        self._decide(PaperStatus.APPROVED, by_id, on, "")

    def reject(self, *, by_id: UUID, on: date, reason: str) -> None:
        reason = reason.strip()
        if not reason or len(reason) > self.REASON_MAX:
            raise _invalid("reason", f"A reason is required, up to {self.REASON_MAX} characters.")
        self._decide(PaperStatus.REJECTED, by_id, on, reason)

    def _decide(self, status: PaperStatus, by_id: UUID, on: date, note: str) -> None:
        if self.status != PaperStatus.SENT:
            raise RuleViolation("Only a sent paper can be decided.")
        if by_id == self.prepared_by_id:
            raise RuleViolation("You cannot decide your own paper.")
        self.status, self.decided_by_id, self.decided_on = status, by_id, on
        self.decision_note = note


# ------------------------------------------------------------------ marks
@dataclass(eq=False, kw_only=True)
class ExamMark(Entity):
    """A student's marks in an exam, or that the student was absent."""

    exam_id: UUID
    student_id: UUID
    marks: int | None = None
    absent: bool = False
    entered_by_id: UUID | None = None

    @classmethod
    def enter(cls, *, exam: Exam, student_id: UUID, marks: int | None, absent: bool,
              entered_by_id: UUID) -> "ExamMark":
        if absent and marks is not None:
            raise _invalid("marks", "An absent student has no marks.")
        if not absent:
            if marks is None:
                raise _invalid("marks", "Give the marks, or mark the student absent.")
            if not 0 <= marks <= exam.max_marks:
                raise _invalid("marks", f"Between 0 and {exam.max_marks}.")
        return cls(exam_id=exam.id, student_id=student_id, marks=marks, absent=absent,
                   entered_by_id=entered_by_id)


@dataclass(frozen=True)
class ResultLine:
    student: Student
    mark: ExamMark | None
    percentage: Decimal | None


@dataclass(frozen=True)
class ExamResults:
    """Every student of the class in one exam, and how the class did."""

    exam: Exam
    lines: list[ResultLine]
    entered: int
    absent: int
    average: Decimal | None
    highest: int | None
    lowest: int | None


@dataclass(frozen=True)
class StudentExamLine:
    exam: Exam
    mark: ExamMark | None
    percentage: Decimal | None


@dataclass(frozen=True)
class StudentResults:
    """One student's exams, with the total over the exams where they have marks."""

    student: Student
    lines: list[StudentExamLine]
    total_obtained: int
    total_out_of: int
    percentage: Decimal | None
