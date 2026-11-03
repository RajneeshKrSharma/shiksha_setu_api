from datetime import date
from decimal import Decimal
from uuid import UUID

from apps.accounts.domain.capabilities import VIEW_ANALYTICS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.attendance.domain.entities import StudentStatus
from apps.attendance.domain.repositories import StudentMarkRepository
from apps.core.domain.clock import Clock
from apps.core.domain.errors import NotFound
from apps.core.domain.money import ZERO
from apps.core.domain.usecase import UseCase
from apps.exams.domain.entities import ExamType, percent
from apps.exams.domain.repositories import ExamRepository
from apps.exams.domain.services import ResultBuilder
from apps.students.domain.repositories import (
    ClassRepository,
    FeePaymentRepository,
    StudentRepository,
)
from apps.students.domain.services import StatementBuilder

from ..ranges import DateRange
from ..reports import (
    AttendancePoint,
    ClassBalance,
    ExamAverages,
    ExamPoint,
    FeeMonth,
    FeeReport,
    StudentAttendanceTrend,
)


class _Report(UseCase):
    def __init__(self, authorizer: Authorizer, clock: Clock):
        self._authorizer = authorizer
        self._clock = clock

    def _allow(self, actor: UserAccount) -> None:
        self._authorizer.require(actor, VIEW_ANALYTICS)


class GetStudentAttendance(_Report):
    """Each day's attendance: how many were present, late and absent, and the percentage who
    came (present plus late, out of those marked). Days nobody was marked are left out."""

    def __init__(self, marks: StudentMarkRepository, classes: ClassRepository,
                 authorizer: Authorizer, clock: Clock):
        super().__init__(authorizer, clock)
        self._marks = marks
        self._classes = classes

    def call(self, actor: UserAccount, *, from_date: date | None = None,
             to_date: date | None = None, class_id: UUID | None = None) -> StudentAttendanceTrend:
        self._allow(actor)
        period = DateRange.daily(from_date, to_date, today=self._clock.today())
        class_name = ""
        if class_id is not None:
            school_class = self._classes.get(class_id)
            if school_class is None:
                raise NotFound("This class was not found.")
            class_name = school_class.name
        counts = self._marks.daily_counts(period.start, period.end, class_id)
        points = []
        for day in sorted(counts):
            by = counts[day]
            present, late, absent = (by.get(s, 0) for s in
                                     (StudentStatus.PRESENT, StudentStatus.LATE, StudentStatus.ABSENT))
            marked = present + late + absent
            points.append(AttendancePoint(
                day=day, marked=marked, present=present, late=late, absent=absent,
                percent=percent(present + late, marked) if marked else None,
            ))
        return StudentAttendanceTrend(period, class_id, class_name, points)


class GetFeeReport(_Report):
    """What was collected each month (by fee), and what is still owed by each class."""

    def __init__(self, payments: FeePaymentRepository, students: StudentRepository,
                 statements: StatementBuilder, authorizer: Authorizer, clock: Clock):
        super().__init__(authorizer, clock)
        self._payments = payments
        self._students = students
        self._statements = statements

    def call(self, actor: UserAccount, *, from_date: date | None = None,
             to_date: date | None = None) -> FeeReport:
        self._allow(actor)
        period = DateRange.monthly(from_date, to_date, today=self._clock.today())
        collected = self._payments.collected_by_month(period.start, period.end)
        months = []
        for month in period.months():
            by_head = collected.get(month, {})
            months.append(FeeMonth(
                month=month, by_head={head.value: amount for head, amount in by_head.items()},
                total=sum(by_head.values(), ZERO),
            ))
        by_class = self._class_balances()
        return FeeReport(
            period=period, collected=months,
            collected_total=sum((m.total for m in months), ZERO),
            by_class=by_class, balance_total=sum((c.balance for c in by_class), ZERO),
        )

    def _class_balances(self) -> list[ClassBalance]:
        grouped: dict[UUID, dict] = {}
        for student in self._students.list(active=True):
            statement = self._statements.build(student)
            entry = grouped.setdefault(student.class_id, {
                "name": student.class_name, "students": 0, "due": ZERO, "paid": ZERO,
            })
            entry["students"] += 1
            entry["due"] += statement.total_due
            entry["paid"] += statement.total_paid
        return [
            ClassBalance(class_id=class_id, class_name=e["name"], students=e["students"],
                         due=e["due"], paid=e["paid"], balance=e["due"] - e["paid"])
            for class_id, e in grouped.items()
        ]


class GetExamAverages(_Report):
    """How each exam went: students marked, absent, and the average marks and percentage."""

    def __init__(self, exams: ExamRepository, results: ResultBuilder, authorizer: Authorizer,
                 clock: Clock):
        super().__init__(authorizer, clock)
        self._exams = exams
        self._results = results

    def call(self, actor: UserAccount, *, from_date: date | None = None,
             to_date: date | None = None, class_id: UUID | None = None,
             exam_type: ExamType | None = None) -> ExamAverages:
        self._allow(actor)
        period = DateRange.monthly(from_date, to_date, today=self._clock.today())
        points = []
        for exam in self._exams.list(class_id=class_id, exam_type=exam_type,
                                     from_date=period.start, to_date=period.end):
            results = self._results.for_exam(exam)
            average: Decimal | None = results.average
            points.append(ExamPoint(
                exam_id=exam.id, held_on=exam.held_on, exam_type=exam.exam_type.value,
                class_name=exam.class_name, subject=exam.subject, max_marks=exam.max_marks,
                entered=results.entered, absent=results.absent, average_marks=average,
                average_percent=percent(average, exam.max_marks) if average is not None else None,
            ))
        return ExamAverages(period, points)
