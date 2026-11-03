from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import Role, UserAccount
from ..ports import PasswordPolicy
from ..repositories import UserRepository


class BootstrapPrincipal(UseCase):
    """The very first sign-in of a school. There is exactly one Principal, and no
    one else can create it, so no actor is needed."""

    def __init__(self, users: UserRepository, passwords: PasswordPolicy, audit: AuditLogger):
        self._users = users
        self._passwords = passwords
        self._audit = audit

    def call(self, *, name: str, email: str, password: str) -> UserAccount:
        if self._users.has_role(Role.PRINCIPAL):
            raise RuleViolation("A Principal already exists.")
        account = UserAccount.register(name=name, email=email, role=Role.PRINCIPAL)
        self._passwords.validate(password, account)
        saved = self._users.add(account, password)
        self._audit.record(None, "principal_created", f"user:{saved.id}")
        return saved
