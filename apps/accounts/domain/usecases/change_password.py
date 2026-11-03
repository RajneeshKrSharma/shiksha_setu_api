from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import UserAccount
from ..ports import PasswordPolicy
from ..repositories import UserRepository


class ChangePassword(UseCase):
    def __init__(self, users: UserRepository, passwords: PasswordPolicy, audit: AuditLogger):
        self._users = users
        self._passwords = passwords
        self._audit = audit

    def call(self, actor: UserAccount, current: str, new: str) -> None:
        if not self._users.check_password(actor.id, current):
            raise RuleViolation("Your current password is wrong.", code="wrong_current_password")
        self._passwords.validate(new, actor)
        self._users.set_password(actor.id, new)
        self._audit.record(actor.id, "password_changed", f"user:{actor.id}")
