"""What each graph is made of. Plain numbers, ready to draw."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from .ranges import DateRange


@dataclass(frozen=True)
class AttendancePoint:
    day: date
    marked: int
    present: int
    late: int
    absent: int
    percent: Decimal | None  # present plus late, out of those marked


@dataclass(frozen=True)
class StudentAttendanceTrend:
    period: DateRange
    class_id: UUID | None
    class_name: str
    points: list[AttendancePoint] = field(default_factory=list)


@dataclass(frozen=True)
class FeeMonth:
    month: date
    by_head: dict[str, Decimal]
    total: Decimal


@dataclass(frozen=True)
class ClassBalance:
    class_id: UUID
    class_name: str
    students: int
    due: Decimal
    paid: Decimal
    balance: Decimal


@dataclass(frozen=True)
class FeeReport:
    period: DateRange
    collected: list[FeeMonth]
    collected_total: Decimal
    by_class: list[ClassBalance]
    balance_total: Decimal


@dataclass(frozen=True)
class ExamPoint:
    exam_id: UUID
    held_on: date
    exam_type: str
    class_name: str
    subject: str
    max_marks: int
    entered: int
    absent: int
    average_marks: Decimal | None
    average_percent: Decimal | None


@dataclass(frozen=True)
class ExamAverages:
    period: DateRange
    points: list[ExamPoint] = field(default_factory=list)


@dataclass(frozen=True)
class StaffDayPoint:
    day: date
    is_holiday: bool
    people: int
    present: int
    late: int
    absent: int
    leave: int
    not_in_yet: int


@dataclass(frozen=True)
class StaffAttendanceTrend:
    period: DateRange
    role: str | None
    points: list[StaffDayPoint] = field(default_factory=list)


@dataclass(frozen=True)
class PaidMonth:
    month: date
    salary: Decimal
    fuel: Decimal
    total: Decimal


@dataclass(frozen=True)
class PaymentsReport:
    period: DateRange
    paid: list[PaidMonth]
    paid_total: Decimal
    owed_salary: Decimal
    owed_fuel: Decimal


@dataclass(frozen=True)
class FuelPoint:
    month: date
    van_id: UUID
    van_name: str
    bills: int
    litres: Decimal
    amount: Decimal
    distance_km: int
    km_per_litre: Decimal | None


@dataclass(frozen=True)
class FuelReport:
    period: DateRange
    points: list[FuelPoint] = field(default_factory=list)


@dataclass(frozen=True)
class LessonPoint:
    day: date
    is_holiday: bool
    expected: int
    recorded: int
    percent: Decimal | None


@dataclass(frozen=True)
class LessonCoverage:
    period: DateRange
    points: list[LessonPoint] = field(default_factory=list)
