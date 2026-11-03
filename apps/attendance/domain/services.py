from __future__ import annotations

from datetime import date, time
from uuid import UUID

from apps.accounts.domain.capabilities import VIEW_ATTENDANCE
from apps.accounts.domain.entities import Role, UserAccount
from apps.accounts.domain.repositories import UserRepository
from apps.accounts.domain.services import Authorizer
from apps.core.domain.errors import NotFound
from apps.school.domain.repositories import HolidayRepository, ScheduleRepository, SchoolRepository
from apps.students.domain.entities import SchoolClass
from apps.students.domain.ports import ClassAccess
from apps.students.domain.repositories import ClassRepository

from .entities import DayStatus, WorkAttendance

# Everyone who logs in and out: teachers, staff and the Vice Principal.
ATTENDING_ROLES = (Role.TEACHER, Role.STAFF, Role.VICE_PRINCIPAL)


class ClassScope:
    """Which classes a person may look at or mark: anyone who checks attendance, all of
    them; a teacher, the classes allotted to them."""

    def __init__(self, classes: ClassRepository, authorizer: Authorizer, access: ClassAccess):
        self._classes = classes
        self._authorizer = authorizer
        self._access = access

    def class_for(self, actor: UserAccount, class_id: UUID) -> SchoolClass:
        school_class = self._classes.get(class_id)
        if school_class is None or not school_class.is_active:
            raise NotFound("This class was not found.")
        if not self._authorizer.can(actor, VIEW_ATTENDANCE):
            visible = self._access.visible_class_ids(actor)
            if visible is not None and class_id not in visible:
                raise NotFound("This class was not found.")
        return school_class


class SchoolHours:
    """When the school opens, from the season the Principal has chosen."""

    def __init__(self, schools: SchoolRepository, schedules: ScheduleRepository,
                 holidays: HolidayRepository):
        self._schools = schools
        self._schedules = schedules
        self._holidays = holidays

    def opens_at(self) -> time | None:
        season = self._schools.current().active_season
        schedule = self._schedules.get(season) if season else None
        return schedule.opens_at if schedule else None

    def is_holiday(self, day: date) -> bool:
        return bool(self._holidays.list(from_date=day, to_date=day))


class DayStatusRule:
    """Works out how a day looks for someone who may not have logged in at all."""

    def status(self, record: WorkAttendance | None, *, day: date, today: date,
               is_holiday: bool, on_leave: bool = False) -> DayStatus:
        if record is not None:
            return DayStatus(record.status.value)
        if is_holiday:
            return DayStatus.HOLIDAY
        if on_leave:
            return DayStatus.LEAVE
        return DayStatus.NOT_IN_YET if day == today else DayStatus.ABSENT


class AttendingPeople:
    """The active people who log in and out, by role and then name."""

    def __init__(self, users: UserRepository):
        self._users = users

    def list(self, role: Role | None = None) -> list[UserAccount]:
        roles = (role,) if role else ATTENDING_ROLES
        return [a for r in roles for a in self._users.list(role=r, active=True)]
