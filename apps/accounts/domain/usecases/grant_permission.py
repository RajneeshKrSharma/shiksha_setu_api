from uuid import UUID

from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase

from ..capabilities import GRANT_PERMISSIONS, CapabilityCatalog
from ..entities import PermissionGrant, Role, UserAccount
from ..repositories import GrantRepository, UserRepository
from ..services import Authorizer


class GrantPermission(UseCase):
    def __init__(self, users: UserRepository, grants: GrantRepository,
                 authorizer: Authorizer, catalog: CapabilityCatalog, audit: AuditLogger):
        self._users = users
        self._grants = grants
        self._authorizer = authorizer
        self._catalog = catalog
        self._audit = audit

    def call(self, actor: UserAccount, *, user_id: UUID, capability: str,
             reason: str) -> PermissionGrant:
        self._authorizer.require(actor, GRANT_PERMISSIONS)

        permission = self._catalog.get(capability)
        if not permission.grantable:
            raise RuleViolation("This permission can never be given to anyone else.",
                                errors={"capability": ["Not grantable."]})
        target = self._users.get(user_id)
        if target is None:
            raise NotFound("This person was not found.")
        if target.role != Role.VICE_PRINCIPAL:
            raise RuleViolation("Permissions can be given only to the Vice Principal.")
        if not target.is_active:
            raise RuleViolation("This account is deactivated.")
        if self._grants.find_active(user_id, permission.code) is not None:
            raise RuleViolation("This permission is already given.")

        grant = PermissionGrant.issue(user_id=user_id, capability=permission.code,
                                      reason=reason, granted_by_id=actor.id)
        saved = self._grants.add(grant)
        self._audit.record(actor.id, "permission_granted", f"user:{user_id}",
                           {"capability": permission.code, "reason": grant.reason})
        return saved
