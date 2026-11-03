from uuid import UUID

from apps.accounts.domain.capabilities import MANAGE_STUDENTS, VIEW_STUDENTS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase
from apps.core.domain.usecases.member_crud import (
    AddMember,
    DeactivateMember,
    GetMember,
    UpdateMember,
)

from ..entities import SchoolClass, Student
from ..ports import ClassAccess
from ..repositories import ClassRepository, StudentRepository

_READERS = (VIEW_STUDENTS, MANAGE_STUDENTS)


class _StudentRules(UseCase):
    """What every change to a student has to respect."""

    def __init__(self, students: StudentRepository, classes: ClassRepository,
                 authorizer: Authorizer, audit: AuditLogger):
        self._students = students
        self._classes = classes
        self._authorizer = authorizer
        self._audit = audit

    def _active_class(self, class_id: UUID) -> SchoolClass:
        school_class = self._classes.get(class_id)
        if school_class is None or not school_class.is_active:
            raise RuleViolation("This class does not exist.",
                                errors={"class_id": ["Choose an existing class."]})
        return school_class

    def _next_roll_number(self, class_id: UUID) -> str:
        """One more than the highest number in the class (students whose roll number is not
        a number are left out of the count)."""
        taken = [int(s.roll_number) for s in self._students.list(class_id=class_id, active=True)
                 if s.roll_number.isdigit()]
        return str(max(taken, default=0) + 1)

    def _ensure_roll_free(self, student: Student) -> None:
        holder = self._students.find_active_by_roll(student.class_id, student.roll_number)
        if holder is not None and holder.id != student.id:
            message = "This roll number is already used in the class."
            raise RuleViolation(message, errors={"roll_number": [message]})


class ListStudents(UseCase):
    """Everyone who manages students sees all; a teacher sees the students of the
    classes they are allotted."""

    def __init__(self, students: StudentRepository, authorizer: Authorizer, access: ClassAccess):
        self._students = students
        self._authorizer = authorizer
        self._access = access

    def call(self, actor: UserAccount, *, query: str = "", active: bool | None = True,
             class_id: UUID | None = None) -> list[Student]:
        self._authorizer.require_any(actor, *_READERS)
        visible = self._access.visible_class_ids(actor)
        if visible is not None and class_id is not None and class_id not in visible:
            return []
        found = self._students.list(query=query.strip(), active=active, class_id=class_id)
        return found if visible is None else [s for s in found if s.class_id in visible]


class GetStudent(UseCase):
    def __init__(self, get: GetMember[Student], authorizer: Authorizer, access: ClassAccess):
        self._get = get
        self._authorizer = authorizer
        self._access = access

    def call(self, actor: UserAccount, student_id: UUID) -> Student:
        self._authorizer.require_any(actor, *_READERS)
        student = self._get.call(student_id)
        visible = self._access.visible_class_ids(actor)
        if visible is not None and student.class_id not in visible:
            raise NotFound("This person was not found.")
        return student


class AddStudent(_StudentRules):
    def __init__(self, add: AddMember[Student], students: StudentRepository,
                 classes: ClassRepository, authorizer: Authorizer, audit: AuditLogger):
        super().__init__(students, classes, authorizer, audit)
        self._add = add

    def call(self, actor: UserAccount, *, name: str, roll_number: str, class_id: UUID,
             guardian_name: str, uses_van: bool = False) -> Student:
        self._authorizer.require(actor, MANAGE_STUDENTS)
        self._active_class(class_id)
        if not roll_number.strip():
            roll_number = self._next_roll_number(class_id)
        student = Student.admit(name=name, roll_number=roll_number, class_id=class_id,
                                guardian_name=guardian_name, uses_van=uses_van)
        self._ensure_roll_free(student)
        saved = self._add.call(student)
        self._audit.record(actor.id, "student_added", f"student:{saved.id}", {"name": saved.name})
        return saved


class UpdateStudent(_StudentRules):
    """Changes only what is given. `is_active` false removes the student, true brings
    them back."""

    def __init__(self, get: GetMember[Student], update: UpdateMember[Student],
                 students: StudentRepository, classes: ClassRepository,
                 authorizer: Authorizer, audit: AuditLogger):
        super().__init__(students, classes, authorizer, audit)
        self._get = get
        self._update = update

    def call(self, actor: UserAccount, student_id: UUID, *, name: str | None = None,
             roll_number: str | None = None, class_id: UUID | None = None,
             guardian_name: str | None = None, uses_van: bool | None = None,
             is_active: bool | None = None) -> Student:
        self._authorizer.require(actor, MANAGE_STUDENTS)
        student = self._get.call(student_id)
        student.update_details(
            name=student.name if name is None else name,
            roll_number=student.roll_number if roll_number is None else roll_number,
            guardian_name=student.guardian_name if guardian_name is None else guardian_name,
        )
        if class_id is not None and class_id != student.class_id:
            self._active_class(class_id)
            student.move_to(class_id)
        if uses_van is not None:
            student.uses_van = uses_van
        if is_active is True:
            self._active_class(student.class_id)
            student.activate()
        elif is_active is False:
            student.deactivate()
        if student.is_active:
            self._ensure_roll_free(student)
        saved = self._update.call(student)
        self._audit.record(actor.id, "student_updated", f"student:{saved.id}", {"name": saved.name})
        return saved


class RemoveStudent(UseCase):
    """Delete means inactive: the student's records and fees stay."""

    def __init__(self, deactivate: DeactivateMember[Student], authorizer: Authorizer,
                 audit: AuditLogger):
        self._deactivate = deactivate
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, student_id: UUID) -> None:
        self._authorizer.require(actor, MANAGE_STUDENTS)
        student = self._deactivate.call(student_id)
        self._audit.record(actor.id, "student_removed", f"student:{student_id}",
                           {"name": student.name})
