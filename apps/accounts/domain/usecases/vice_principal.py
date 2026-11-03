from uuid import UUID

from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import NotFound
from apps.core.domain.usecase import UseCase

from ..capabilities import APPOINT_VICE_PRINCIPAL
from ..entities import Role, UserAccount
from ..ports import PasswordPolicy
from ..repositories import GrantRepository, UserRepository
from ..services import Authorizer


class _VicePrincipalUseCase(UseCase):
    """Only the Principal looks after the Vice Principal, so every action asks for the right
    to appoint one."""

    def __init__(self, users: UserRepository, authorizer: Authorizer):
        self._users = users
        self._authorizer = authorizer

    def _vice_principal(self, actor: UserAccount, vice_principal_id: UUID) -> UserAccount:
        self._authorizer.require(actor, APPOINT_VICE_PRINCIPAL)
        account = self._users.get(vice_principal_id)
        if account is None or account.role != Role.VICE_PRINCIPAL:
            raise NotFound("This Vice Principal was not found.")
        return account


class ListVicePrincipals(_VicePrincipalUseCase):
    def call(self, actor: UserAccount, *, query: str = "",
             active: bool | None = True) -> list[UserAccount]:
        self._authorizer.require(actor, APPOINT_VICE_PRINCIPAL)
        return self._users.list(role=Role.VICE_PRINCIPAL, query=query.strip(), active=active)


class GetVicePrincipal(_VicePrincipalUseCase):
    def call(self, actor: UserAccount, vice_principal_id: UUID) -> UserAccount:
        return self._vice_principal(actor, vice_principal_id)


class _Changer(_VicePrincipalUseCase):
    def __init__(self, users: UserRepository, grants: GrantRepository, authorizer: Authorizer,
                 audit: AuditLogger):
        super().__init__(users, authorizer)
        self._grants = grants
        self._audit = audit

    def _take_back_permissions(self, actor: UserAccount, account: UserAccount) -> int:
        """A Vice Principal who is removed loses every permission, so that bringing them back
        later does not quietly bring the old permissions back too."""
        given = self._grants.list(user_id=account.id)
        for grant in given:
            grant.revoke()
            self._grants.update(grant)
            self._audit.record(actor.id, "permission_revoked", f"user:{account.id}",
                               {"capability": grant.capability, "because": "removed"})
        return len(given)


class UpdateVicePrincipal(_Changer):
    """Changes only what is given. The email is the login and does not change.
    `is_active` false removes the Vice Principal (and takes back their permissions);
    a new `password` replaces the old."""

    def __init__(self, users: UserRepository, grants: GrantRepository, passwords: PasswordPolicy,
                 authorizer: Authorizer, audit: AuditLogger):
        super().__init__(users, grants, authorizer, audit)
        self._passwords = passwords

    def call(self, actor: UserAccount, vice_principal_id: UUID, *, name: str | None = None,
             is_active: bool | None = None, password: str | None = None) -> UserAccount:
        account = self._vice_principal(actor, vice_principal_id)
        if name is not None:
            account.rename(name)
        if is_active is True:
            account.activate()
        elif is_active is False:
            account.deactivate()
        if password is not None:
            self._passwords.validate(password, account)
        saved = self._users.update(account)
        if password is not None:
            self._users.set_password(vice_principal_id, password)
        if is_active is False:
            self._take_back_permissions(actor, account)
        self._audit.record(actor.id, "vice_principal_updated", f"user:{vice_principal_id}", {
            "name": saved.name, "is_active": saved.is_active,
            "password_reset": password is not None,
        })
        return saved


class RemoveVicePrincipal(_Changer):
    """Delete means inactive: they can no longer sign in, they lose their permissions, and
    the record stays."""

    def call(self, actor: UserAccount, vice_principal_id: UUID) -> None:
        account = self._vice_principal(actor, vice_principal_id)
        account.deactivate()
        self._users.update(account)
        self._take_back_permissions(actor, account)
        self._audit.record(actor.id, "vice_principal_removed", f"user:{vice_principal_id}",
                           {"name": account.name})
