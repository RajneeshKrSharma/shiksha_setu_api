from collections import Counter
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from apps.accounts.domain.capabilities import VIEW_ANALYTICS
from apps.accounts.domain.entities import Role, UserAccount
from apps.accounts.domain.repositories import UserRepository
from apps.accounts.domain.services import Authorizer
from apps.attendance.domain.entities import DayStatus
from apps.attendance.domain.ports import LeaveCalendar
from apps.attendance.domain.repositories import WorkAttendanceRepository
from apps.attendance.domain.services import (
    ATTENDING_ROLES,
    AttendingPeople,
    DayStatusRule,
    SchoolHours,
)
from apps.core.domain.clock import Clock
from apps.core.domain.errors import RuleViolation
from apps.core.domain.money import ZERO
from apps.core.domain.usecase import UseCase
from apps.exams.domain.entities import percent
from apps.payments.domain.entities import PaymentKind
from apps.payments.domain.repositories import PaymentRepository
from apps.payments.domain.services import StatementBuilder as PayStatementBuilder
from apps.staff.domain.fuel import BillStatus
from apps.staff.domain.repositories import FuelBillRepository
from apps.staff.domain.services import FuelReporter
from apps.teachers.domain.repositories import AllotmentRepository, LessonRepository

from ..ranges import DateRange
from ..reports import (
    FuelPoint,
    FuelReport,
    LessonCoverage,
    LessonPoint,
    PaidMonth,
    PaymentsReport,
    StaffAttendanceTrend,
    StaffDayPoint,
)


class _Report(UseCase):
    def __init__(self, authorizer: Authorizer, clock: Clock):
        self._authorizer = authorizer
        self._clock = clock

    def _allow(self, actor: UserAccount) -> None:
        self._authorizer.require(actor, VIEW_ANALYTICS)


class GetStaffAttendance(_Report):
    """For each day, how many teachers and staff were present, late, absent, on leave, or not
    in yet (today). On a holiday only those who came are counted."""

    def __init__(self, records: WorkAttendanceRepository, people: AttendingPeople,
                 hours: SchoolHours, leaves: LeaveCalendar, rule: DayStatusRule,
                 authorizer: Authorizer, clock: Clock):
        super().__init__(authorizer, clock)
        self._records = records
        self._people = people
        self._hours = hours
        self._leaves = leaves
        self._rule = rule

    def call(self, actor: UserAccount, *, from_date: date | None = None,
             to_date: date | None = None, role: Role | None = None) -> StaffAttendanceTrend:
        self._allow(actor)
        if role is not None and role not in ATTENDING_ROLES:
            raise RuleViolation("Choose teacher, staff or vice_principal.",
                                errors={"role": ["Not a role that logs in and out."]})
        today = self._clock.today()
        period = DateRange.daily(from_date, to_date, today=today)
        people = self._people.list(role)
        points = []
        for day in period.days(up_to=today):
            records = self._records.on_day(day)
            holiday = self._hours.is_holiday(day)
            on_leave = self._leaves.people_on_leave(day)
            seen = Counter(
                self._rule.status(records.get(p.id), day=day, today=today, is_holiday=holiday,
                                  on_leave=p.id in on_leave)
                for p in people
            )
            points.append(StaffDayPoint(
                day=day, is_holiday=holiday, people=len(people),
                present=seen[DayStatus.PRESENT], late=seen[DayStatus.LATE],
                absent=seen[DayStatus.ABSENT], leave=seen[DayStatus.LEAVE],
                not_in_yet=seen[DayStatus.NOT_IN_YET],
            ))
        return StaffAttendanceTrend(period, role.value if role else None, points)


class GetPaymentsReport(_Report):
    """What was paid out each month (salary and fuel), and what teachers and staff are still
    owed today."""

    def __init__(self, payments: PaymentRepository, users: UserRepository,
                 statements: PayStatementBuilder, authorizer: Authorizer, clock: Clock):
        super().__init__(authorizer, clock)
        self._payments = payments
        self._users = users
        self._statements = statements

    def call(self, actor: UserAccount, *, from_date: date | None = None,
             to_date: date | None = None) -> PaymentsReport:
        self._allow(actor)
        today = self._clock.today()
        period = DateRange.monthly(from_date, to_date, today=today)
        paid = self._payments.paid_out_by_month(period.start, period.end)
        months = []
        for month in period.months():
            kinds = paid.get(month, {})
            salary, fuel = kinds.get(PaymentKind.SALARY, ZERO), kinds.get(PaymentKind.FUEL_BILL, ZERO)
            months.append(PaidMonth(month=month, salary=salary, fuel=fuel, total=salary + fuel))

        owed_salary = owed_fuel = ZERO
        for role in (Role.TEACHER, Role.STAFF):
            for person in self._users.list(role=role, active=True):
                statement = self._statements.build(person.id, today)
                owed_salary += statement.salary_balance
                owed_fuel += statement.fuel_balance
        return PaymentsReport(
            period=period, paid=months, paid_total=sum((m.total for m in months), ZERO),
            owed_salary=owed_salary, owed_fuel=owed_fuel,
        )


class GetFuelReport(_Report):
    """Each month and van: bills, litres, money, distance covered and kilometres per litre.
    Only approved bills count."""

    def __init__(self, bills: FuelBillRepository, reporter: FuelReporter,
                 authorizer: Authorizer, clock: Clock):
        super().__init__(authorizer, clock)
        self._bills = bills
        self._reporter = reporter

    def call(self, actor: UserAccount, *, from_date: date | None = None,
             to_date: date | None = None, van_id: UUID | None = None) -> FuelReport:
        self._allow(actor)
        period = DateRange.monthly(from_date, to_date, today=self._clock.today())
        groups: dict[tuple[date, UUID], dict] = {}
        for bill in self._bills.list(van_id=van_id, status=BillStatus.APPROVED,
                                     from_date=period.start, to_date=period.end):
            report = self._reporter.report(bill)
            entry = groups.setdefault((bill.billed_on.replace(day=1), bill.van_id), {
                "van": bill.van_name, "bills": 0, "litres": ZERO, "amount": ZERO,
                "distance": 0, "litres_with_distance": ZERO,
            })
            entry["bills"] += 1
            entry["litres"] += bill.litres
            entry["amount"] += bill.amount
            if report.distance_km is not None:
                entry["distance"] += report.distance_km
                entry["litres_with_distance"] += bill.litres
        points = []
        for (month, vid), e in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[1]["van"])):
            per_litre = (
                (Decimal(e["distance"]) / e["litres_with_distance"]).quantize(ZERO, rounding=ROUND_HALF_UP)
                if e["litres_with_distance"] else None
            )
            points.append(FuelPoint(month=month, van_id=vid, van_name=e["van"], bills=e["bills"],
                                    litres=e["litres"], amount=e["amount"],
                                    distance_km=e["distance"], km_per_litre=per_litre))
        return FuelReport(period, points)


class GetLessonCoverage(_Report):
    """For each day, how many of the lessons expected (one per active class-and-subject
    allotment of a teacher who can sign in) were recorded. The expected number is today's
    allotments, as the school keeps no history of them."""

    def __init__(self, allotments: AllotmentRepository, lessons: LessonRepository,
                 hours: SchoolHours, authorizer: Authorizer, clock: Clock):
        super().__init__(authorizer, clock)
        self._allotments = allotments
        self._lessons = lessons
        self._hours = hours

    def call(self, actor: UserAccount, *, from_date: date | None = None,
             to_date: date | None = None) -> LessonCoverage:
        self._allow(actor)
        today = self._clock.today()
        period = DateRange.daily(from_date, to_date, today=today)
        expected_ids = {a.id for a in self._allotments.list(teacher_active=True)}
        points = []
        for day in period.days(up_to=today):
            recorded = sum(1 for allotment_id in self._lessons.on_day(day) if allotment_id in expected_ids)
            points.append(LessonPoint(
                day=day, is_holiday=self._hours.is_holiday(day), expected=len(expected_ids),
                recorded=recorded,
                percent=percent(recorded, len(expected_ids)) if expected_ids else None,
            ))
        return LessonCoverage(period, points)
