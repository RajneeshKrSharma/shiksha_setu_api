from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import Forbidden, RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import Role, UserAccount
from ..policies import PolicyRegistry
from ..ports import PasswordPolicy
from ..repositories import UserRepository
from ..services import Authorizer


class CreateAccount(UseCase):
    """Makes a login for a Vice Principal, teacher or staff member. Which right the
    actor needs depends on the role being created, and the role's policy says so."""

    def __init__(self, users: UserRepository, policies: PolicyRegistry,
                 authorizer: Authorizer, passwords: PasswordPolicy, audit: AuditLogger):
        self._users = users
        self._policies = policies
        self._authorizer = authorizer
        self._passwords = passwords
        self._audit = audit

    def call(self, actor: UserAccount, *, name: str, email: str, role: Role,
             password: str) -> UserAccount:
        right = self._policies.for_role(role).creation_right
        if right is None:
            raise Forbidden("This kind of account cannot be created here.")
        self._authorizer.require(actor, right)

        account = UserAccount.register(name=name, email=email, role=role)
        if self._users.get_by_email(account.email) is not None:
            message = "A user with this email already exists."
            raise RuleViolation(message, errors={"email": [message]})
        self._passwords.validate(password, account)

        saved = self._users.add(account, password)
        self._audit.record(actor.id, "account_created", f"user:{saved.id}",
                           {"role": role.value})
        return saved
