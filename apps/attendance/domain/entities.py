from dataclasses import dataclass, field
from datetime import date, time
from enum import StrEnum
from uuid import UUID

from apps.core.domain.entity import Entity
from apps.core.domain.errors import RuleViolation
from apps.students.domain.entities import Student


class StudentStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"


class WorkStatus(StrEnum):
    PRESENT = "present"
    LATE = "late"


class DayStatus(StrEnum):
    """How a teacher's or staff member's day looks to the Principal."""

    PRESENT = "present"
    LATE = "late"
    ABSENT = "absent"  # a past day, no check-in, not a holiday, not on leave
    LEAVE = "leave"  # on approved leave
    HOLIDAY = "holiday"
    NOT_IN_YET = "not_in_yet"  # today, no check-in yet


@dataclass(eq=False, kw_only=True)
class StudentMark(Entity):
    """One student's attendance for one day."""

    student_id: UUID
    class_id: UUID
    day: date
    status: StudentStatus
    marked_by_id: UUID | None = None


@dataclass(frozen=True)
class RosterLine:
    """A student of the class with their mark for the day, or None while unmarked."""

    student: Student
    mark: StudentMark | None


@dataclass(frozen=True)
class StudentTally:
    student: Student
    present: int
    late: int
    absent: int


@dataclass(eq=False, kw_only=True)
class WorkAttendance(Entity):
    """A teacher's or staff member's day: when they logged in and when they logged out."""

    person_id: UUID
    day: date
    checked_in_at: time
    checked_out_at: time | None = None
    status: WorkStatus = WorkStatus.PRESENT
    corrected_by_id: UUID | None = None
    # Filled in when read, so the app can show them.
    person_name: str = ""
    role: str = ""

    @classmethod
    def arrive(cls, *, person_id: UUID, day: date, at: time, opens_at: time | None) -> "WorkAttendance":
        record = cls(person_id=person_id, day=day, checked_in_at=at)
        record.status = record._status_for(opens_at)
        return record

    def depart(self, at: time) -> None:
        if self.checked_out_at is not None:
            raise RuleViolation("You have already checked out today.")
        self._set_times(self.checked_in_at, at)

    def correct(self, *, checked_in_at: time, checked_out_at: time | None, opens_at: time | None,
                by_id: UUID) -> None:
        self._set_times(checked_in_at, checked_out_at)
        self.status = self._status_for(opens_at)
        self.corrected_by_id = by_id

    def _set_times(self, checked_in_at: time, checked_out_at: time | None) -> None:
        if checked_out_at is not None and checked_out_at < checked_in_at:
            message = "The check-out time cannot be before the check-in time."
            raise RuleViolation(message, errors={"checked_out_at": [message]})
        self.checked_in_at, self.checked_out_at = checked_in_at, checked_out_at

    def _status_for(self, opens_at: time | None) -> WorkStatus:
        late = opens_at is not None and self.checked_in_at > opens_at
        return WorkStatus.LATE if late else WorkStatus.PRESENT


@dataclass(frozen=True)
class PersonDay:
    """One person's day on the Principal's board."""

    person_id: UUID
    name: str
    role: str
    status: DayStatus
    record: WorkAttendance | None = None


@dataclass(frozen=True)
class DayBoard:
    day: date
    is_holiday: bool
    people: list[PersonDay] = field(default_factory=list)
