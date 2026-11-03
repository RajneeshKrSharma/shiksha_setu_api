from datetime import date
from uuid import UUID

from apps.accounts.domain.capabilities import (
    CORRECT_ATTENDANCE,
    MARK_STUDENT_ATTENDANCE,
    VIEW_ATTENDANCE,
)
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.clock import Clock
from apps.core.domain.errors import RuleViolation
from apps.core.domain.usecase import UseCase
from apps.students.domain.repositories import StudentRepository

from ..entities import RosterLine, StudentMark, StudentStatus, StudentTally
from ..repositories import StudentMarkRepository
from ..services import ClassScope

_READERS = (VIEW_ATTENDANCE, MARK_STUDENT_ATTENDANCE)


class _ClassDay(UseCase):
    """A class on one day: the students and the marks so far."""

    def __init__(self, students: StudentRepository, marks: StudentMarkRepository,
                 scope: ClassScope, authorizer: Authorizer, clock: Clock):
        self._students = students
        self._marks = marks
        self._scope = scope
        self._authorizer = authorizer
        self._clock = clock

    def _day(self, day: date | None) -> date:
        today = self._clock.today()
        day = day or today
        if day > today:
            raise RuleViolation("Attendance cannot be taken for a future day.",
                                errors={"day": ["Not a future day."]})
        return day

    def _roster(self, class_id: UUID, day: date) -> list[RosterLine]:
        marks = self._marks.for_class_day(class_id, day)
        students = self._students.list(class_id=class_id, active=True)
        return [RosterLine(student, marks.get(student.id)) for student in students]


class GetClassAttendance(_ClassDay):
    def call(self, actor: UserAccount, *, class_id: UUID,
             day: date | None = None) -> list[RosterLine]:
        self._authorizer.require_any(actor, *_READERS)
        self._scope.class_for(actor, class_id)
        return self._roster(class_id, self._day(day))


class MarkStudentAttendance(_ClassDay):
    """A teacher marks their class for today; fixing a past day needs the right to
    correct attendance. Students left out of the list stay unmarked, and a student marked
    again gets the new mark."""

    def __init__(self, students: StudentRepository, marks: StudentMarkRepository,
                 scope: ClassScope, authorizer: Authorizer, clock: Clock, audit: AuditLogger):
        super().__init__(students, marks, scope, authorizer, clock)
        self._audit = audit

    def call(self, actor: UserAccount, *, class_id: UUID,
             marks: list[tuple[UUID, StudentStatus]], day: date | None = None) -> list[RosterLine]:
        self._authorizer.require(actor, MARK_STUDENT_ATTENDANCE)
        school_class = self._scope.class_for(actor, class_id)
        day = self._day(day)
        corrected = day != self._clock.today()
        if corrected:
            self._authorizer.require(actor, CORRECT_ATTENDANCE)
        if not marks:
            raise RuleViolation("Mark at least one student.", errors={"marks": ["Required."]})

        in_class = {s.id for s in self._students.list(class_id=class_id, active=True)}
        seen: set[UUID] = set()
        entries = []
        for student_id, status in marks:
            if student_id not in in_class:
                raise RuleViolation("A student in the list is not in this class.",
                                    errors={"marks": ["Not a student of this class."]})
            if student_id in seen:
                raise RuleViolation("A student is in the list twice.",
                                    errors={"marks": ["Each student once."]})
            seen.add(student_id)
            entries.append(StudentMark(student_id=student_id, class_id=class_id, day=day,
                                       status=status, marked_by_id=actor.id))
        self._marks.save_many(entries)
        if corrected:
            self._audit.record(actor.id, "student_attendance_corrected", f"class:{class_id}", {
                "class": school_class.name, "day": day.isoformat(), "students": len(entries),
            })
        return self._roster(class_id, day)


class StudentAttendanceReport(UseCase):
    """How many days each student of a class was present, late and absent, between two dates."""

    MAX_DAYS = 366

    def __init__(self, students: StudentRepository, marks: StudentMarkRepository,
                 scope: ClassScope, authorizer: Authorizer):
        self._students = students
        self._marks = marks
        self._scope = scope
        self._authorizer = authorizer

    def call(self, actor: UserAccount, *, class_id: UUID, from_date: date,
             to_date: date) -> list[StudentTally]:
        self._authorizer.require_any(actor, *_READERS)
        self._scope.class_for(actor, class_id)
        if to_date < from_date or (to_date - from_date).days >= self.MAX_DAYS:
            raise RuleViolation(f"Choose dates in order, within {self.MAX_DAYS} days.",
                                errors={"to": ["Check the dates."]})
        counts = self._marks.tally(class_id, from_date, to_date)
        return [
            StudentTally(
                student,
                present=counts.get(student.id, {}).get(StudentStatus.PRESENT, 0),
                late=counts.get(student.id, {}).get(StudentStatus.LATE, 0),
                absent=counts.get(student.id, {}).get(StudentStatus.ABSENT, 0),
            )
            for student in self._students.list(class_id=class_id, active=True)
        ]
