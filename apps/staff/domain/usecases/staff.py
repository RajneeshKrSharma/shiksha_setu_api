from uuid import UUID

from apps.accounts.domain.capabilities import ALLOT_VANS, MANAGE_STAFF
from apps.accounts.domain.entities import Role, UserAccount
from apps.accounts.domain.ports import PasswordPolicy
from apps.accounts.domain.repositories import UserRepository
from apps.accounts.domain.services import Authorizer
from apps.accounts.domain.usecases.create_account import CreateAccount
from apps.core.domain.audit import AuditLogger
from apps.core.domain.usecase import UseCase
from apps.core.domain.usecases.member_crud import DeactivateMember, GetMember, UpdateMember

from ..entities import StaffMember
from ..repositories import StaffRepository
from ..services import DrivingRule

_READERS = (MANAGE_STAFF, ALLOT_VANS)


class ListStaff(UseCase):
    def __init__(self, staff: StaffRepository, authorizer: Authorizer):
        self._staff = staff
        self._authorizer = authorizer

    def call(self, actor: UserAccount, *, query: str = "",
             active: bool | None = True) -> list[StaffMember]:
        self._authorizer.require_any(actor, *_READERS)
        return self._staff.list(query=query.strip(), active=active)


class GetStaff(UseCase):
    def __init__(self, get: GetMember[StaffMember], authorizer: Authorizer):
        self._get = get
        self._authorizer = authorizer

    def call(self, actor: UserAccount, staff_id: UUID) -> StaffMember:
        self._authorizer.require_any(actor, *_READERS)
        return self._get.call(staff_id)


class AddStaff(UseCase):
    """Makes the login through the accounts module (which checks the right, the email and
    the password and writes the audit record), then saves the job title."""

    def __init__(self, create_account: CreateAccount, staff: StaffRepository):
        self._create_account = create_account
        self._staff = staff

    def call(self, actor: UserAccount, *, name: str, email: str, password: str,
             job_title: str) -> StaffMember:
        job_title = StaffMember.clean_title(job_title)
        account = self._create_account.call(
            actor, name=name, email=email, role=Role.STAFF, password=password
        )
        self._staff.set_job_title(account.id, job_title)
        return StaffMember.from_account(account, job_title)


class UpdateStaff(UseCase):
    """Changes only what is given. The email is the login and does not change.
    `is_active` false stops the person signing in; a new `password` replaces the old."""

    def __init__(self, get: GetMember[StaffMember], update: UpdateMember[StaffMember],
                 users: UserRepository, passwords: PasswordPolicy, driving: DrivingRule,
                 authorizer: Authorizer, audit: AuditLogger):
        self._get = get
        self._update = update
        self._users = users
        self._passwords = passwords
        self._driving = driving
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, staff_id: UUID, *, name: str | None = None,
             job_title: str | None = None, is_active: bool | None = None,
             password: str | None = None) -> StaffMember:
        self._authorizer.require(actor, MANAGE_STAFF)
        staff = self._get.call(staff_id)
        if name is not None:
            staff.rename(name)
        if job_title is not None:
            staff.retitle(job_title)
        if is_active is True:
            staff.activate()
        elif is_active is False:
            self._driving.ensure_not_driving(staff_id)
            staff.deactivate()
        if password is not None:
            self._passwords.validate(password, self._users.get(staff_id))
        saved = self._update.call(staff)
        if password is not None:
            self._users.set_password(staff_id, password)
        self._audit.record(actor.id, "staff_updated", f"user:{staff_id}", {
            "name": saved.name, "job_title": saved.job_title, "is_active": saved.is_active,
            "password_reset": password is not None,
        })
        return saved


class RemoveStaff(UseCase):
    """Delete means inactive: the person can no longer sign in, and the record stays."""

    def __init__(self, deactivate: DeactivateMember[StaffMember], driving: DrivingRule,
                 authorizer: Authorizer, audit: AuditLogger):
        self._deactivate = deactivate
        self._driving = driving
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, staff_id: UUID) -> None:
        self._authorizer.require(actor, MANAGE_STAFF)
        self._driving.ensure_not_driving(staff_id)
        staff = self._deactivate.call(staff_id)
        self._audit.record(actor.id, "staff_removed", f"user:{staff_id}", {"name": staff.name})
