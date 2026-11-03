from uuid import UUID

from apps.accounts.domain.capabilities import ALLOT_CLASSES, MANAGE_TEACHERS
from apps.accounts.domain.entities import Role, UserAccount
from apps.accounts.domain.ports import PasswordPolicy
from apps.accounts.domain.repositories import UserRepository
from apps.accounts.domain.services import Authorizer
from apps.accounts.domain.usecases.create_account import CreateAccount
from apps.core.domain.audit import AuditLogger
from apps.core.domain.usecase import UseCase
from apps.core.domain.usecases.member_crud import DeactivateMember, GetMember, UpdateMember

from ..entities import Teacher
from ..repositories import TeacherRepository

_READERS = (MANAGE_TEACHERS, ALLOT_CLASSES)


class ListTeachers(UseCase):
    def __init__(self, teachers: TeacherRepository, authorizer: Authorizer):
        self._teachers = teachers
        self._authorizer = authorizer

    def call(self, actor: UserAccount, *, query: str = "", active: bool | None = True) -> list[Teacher]:
        self._authorizer.require_any(actor, *_READERS)
        return self._teachers.list(query=query.strip(), active=active)


class GetTeacher(UseCase):
    def __init__(self, get: GetMember[Teacher], authorizer: Authorizer):
        self._get = get
        self._authorizer = authorizer

    def call(self, actor: UserAccount, teacher_id: UUID) -> Teacher:
        self._authorizer.require_any(actor, *_READERS)
        return self._get.call(teacher_id)


class AddTeacher(UseCase):
    """Makes the teacher's login through the accounts module, which checks the right,
    the email and the password and writes the audit record."""

    def __init__(self, create_account: CreateAccount):
        self._create_account = create_account

    def call(self, actor: UserAccount, *, name: str, email: str, password: str) -> Teacher:
        account = self._create_account.call(
            actor, name=name, email=email, role=Role.TEACHER, password=password
        )
        return Teacher.from_account(account)


class UpdateTeacher(UseCase):
    """Changes only what is given. The email is the login and does not change.
    `is_active` false stops the teacher signing in; a new `password` replaces the old."""

    def __init__(self, get: GetMember[Teacher], update: UpdateMember[Teacher],
                 users: UserRepository, passwords: PasswordPolicy, authorizer: Authorizer,
                 audit: AuditLogger):
        self._get = get
        self._update = update
        self._users = users
        self._passwords = passwords
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, teacher_id: UUID, *, name: str | None = None,
             is_active: bool | None = None, password: str | None = None) -> Teacher:
        self._authorizer.require(actor, MANAGE_TEACHERS)
        teacher = self._get.call(teacher_id)
        if name is not None:
            teacher.rename(name)
        if is_active is True:
            teacher.activate()
        elif is_active is False:
            teacher.deactivate()
        if password is not None:
            self._passwords.validate(password, self._users.get(teacher_id))
        saved = self._update.call(teacher)
        if password is not None:
            self._users.set_password(teacher_id, password)
        self._audit.record(actor.id, "teacher_updated", f"user:{teacher_id}", {
            "name": saved.name, "is_active": saved.is_active, "password_reset": password is not None,
        })
        return saved


class RemoveTeacher(UseCase):
    """Delete means inactive: the teacher can no longer sign in, and the record stays."""

    def __init__(self, deactivate: DeactivateMember[Teacher], authorizer: Authorizer,
                 audit: AuditLogger):
        self._deactivate = deactivate
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, teacher_id: UUID) -> None:
        self._authorizer.require(actor, MANAGE_TEACHERS)
        teacher = self._deactivate.call(teacher_id)
        self._audit.record(actor.id, "teacher_removed", f"user:{teacher_id}", {"name": teacher.name})
