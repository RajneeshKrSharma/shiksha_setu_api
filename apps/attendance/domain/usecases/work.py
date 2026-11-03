from datetime import date, time
from uuid import UUID

from apps.accounts.domain.capabilities import (
    CORRECT_ATTENDANCE,
    RECORD_OWN_ATTENDANCE,
    VIEW_ATTENDANCE,
)
from apps.accounts.domain.entities import Role, UserAccount
from apps.accounts.domain.repositories import UserRepository
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.clock import Clock
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import DayBoard, PersonDay, WorkAttendance
from ..ports import LeaveCalendar
from ..repositories import WorkAttendanceRepository
from ..services import ATTENDING_ROLES, AttendingPeople, DayStatusRule, SchoolHours


class CheckIn(UseCase):
    """The person logs in for today. They are late if it is after the school opens."""

    def __init__(self, records: WorkAttendanceRepository, hours: SchoolHours,
                 authorizer: Authorizer, clock: Clock):
        self._records = records
        self._hours = hours
        self._authorizer = authorizer
        self._clock = clock

    def call(self, actor: UserAccount) -> WorkAttendance:
        self._authorizer.require(actor, RECORD_OWN_ATTENDANCE)
        now = self._clock.now()
        day = now.date()
        if self._records.find(actor.id, day) is not None:
            raise RuleViolation("You have already checked in today.")
        record = WorkAttendance.arrive(
            person_id=actor.id, day=day, at=now.time().replace(microsecond=0),
            opens_at=self._hours.opens_at(),
        )
        return self._records.add(record)


class CheckOut(UseCase):
    def __init__(self, records: WorkAttendanceRepository, authorizer: Authorizer, clock: Clock):
        self._records = records
        self._authorizer = authorizer
        self._clock = clock

    def call(self, actor: UserAccount) -> WorkAttendance:
        self._authorizer.require(actor, RECORD_OWN_ATTENDANCE)
        now = self._clock.now()
        record = self._records.find(actor.id, now.date())
        if record is None:
            raise RuleViolation("Check in first.")
        record.depart(now.time().replace(microsecond=0))
        return self._records.update(record)


class ListMyAttendance(UseCase):
    """The person's own days; today if no dates are given."""

    def __init__(self, records: WorkAttendanceRepository, authorizer: Authorizer, clock: Clock):
        self._records = records
        self._authorizer = authorizer
        self._clock = clock

    def call(self, actor: UserAccount, *, from_date: date | None = None,
             to_date: date | None = None) -> list[WorkAttendance]:
        self._authorizer.require(actor, RECORD_OWN_ATTENDANCE)
        if from_date is None and to_date is None:
            from_date = to_date = self._clock.today()
        return self._records.list(person_id=actor.id, from_date=from_date, to_date=to_date)


class GetDayBoard(UseCase):
    """For the Principal: every teacher and staff member for one day, logged in or not."""

    def __init__(self, records: WorkAttendanceRepository, people: AttendingPeople,
                 hours: SchoolHours, leaves: LeaveCalendar, rule: DayStatusRule,
                 authorizer: Authorizer, clock: Clock):
        self._records = records
        self._people = people
        self._hours = hours
        self._leaves = leaves
        self._rule = rule
        self._authorizer = authorizer
        self._clock = clock

    def call(self, actor: UserAccount, *, day: date | None = None,
             role: Role | None = None) -> DayBoard:
        self._authorizer.require(actor, VIEW_ATTENDANCE)
        if role is not None and role not in ATTENDING_ROLES:
            raise RuleViolation("Choose teacher, staff or vice_principal.",
                                errors={"role": ["Not a role that logs in and out."]})
        today = self._clock.today()
        day = day or today
        if day > today:
            raise RuleViolation("There is no attendance for a future day.",
                                errors={"day": ["Not a future day."]})
        records = self._records.on_day(day)
        holiday = self._hours.is_holiday(day)
        on_leave = self._leaves.people_on_leave(day)
        lines = [
            PersonDay(
                person_id=person.id, name=person.name, role=person.role.value,
                status=self._rule.status(records.get(person.id), day=day, today=today,
                                         is_holiday=holiday, on_leave=person.id in on_leave),
                record=records.get(person.id),
            )
            for person in self._people.list(role)
        ]
        return DayBoard(day=day, is_holiday=holiday, people=lines)


class ListWorkRecords(UseCase):
    def __init__(self, records: WorkAttendanceRepository, authorizer: Authorizer):
        self._records = records
        self._authorizer = authorizer

    def call(self, actor: UserAccount, *, person_id: UUID | None = None,
             from_date: date | None = None, to_date: date | None = None) -> list[WorkAttendance]:
        self._authorizer.require(actor, VIEW_ATTENDANCE)
        return self._records.list(person_id=person_id, from_date=from_date, to_date=to_date)


class CorrectWorkAttendance(UseCase):
    """Fills in a missed check-in or check-out for a day, or fixes the times."""

    def __init__(self, records: WorkAttendanceRepository, users: UserRepository,
                 hours: SchoolHours, authorizer: Authorizer, audit: AuditLogger, clock: Clock):
        self._records = records
        self._users = users
        self._hours = hours
        self._authorizer = authorizer
        self._audit = audit
        self._clock = clock

    def call(self, actor: UserAccount, *, person_id: UUID, day: date, checked_in_at: time,
             checked_out_at: time | None = None) -> WorkAttendance:
        self._authorizer.require(actor, CORRECT_ATTENDANCE)
        person = self._users.get(person_id)
        if person is None or not person.is_active:
            raise NotFound("This person was not found.")
        if person.role not in ATTENDING_ROLES:
            raise RuleViolation("This person does not log in and out.",
                                errors={"person_id": ["Choose a teacher or staff member."]})
        if day > self._clock.today():
            raise RuleViolation("A future day cannot be corrected.",
                                errors={"day": ["Not a future day."]})

        record = self._records.find(person_id, day)
        is_new = record is None
        if is_new:
            record = WorkAttendance(person_id=person_id, day=day, checked_in_at=checked_in_at)
        record.correct(checked_in_at=checked_in_at, checked_out_at=checked_out_at,
                       opens_at=self._hours.opens_at(), by_id=actor.id)
        saved = self._records.add(record) if is_new else self._records.update(record)
        self._audit.record(actor.id, "attendance_corrected", f"user:{person_id}", {
            "day": day.isoformat(), "in": checked_in_at.isoformat(timespec="minutes"),
            "out": checked_out_at.isoformat(timespec="minutes") if checked_out_at else None,
        })
        return saved
