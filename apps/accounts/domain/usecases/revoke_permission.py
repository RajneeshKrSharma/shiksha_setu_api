from uuid import UUID

from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase

from ..capabilities import GRANT_PERMISSIONS
from ..entities import UserAccount
from ..repositories import GrantRepository
from ..services import Authorizer


class RevokePermission(UseCase):
    def __init__(self, grants: GrantRepository, authorizer: Authorizer, audit: AuditLogger):
        self._grants = grants
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, grant_id: UUID) -> None:
        self._authorizer.require(actor, GRANT_PERMISSIONS)
        grant = self._grants.get(grant_id)
        if grant is None:
            raise NotFound("This permission was not found.")
        if not grant.is_active:
            raise RuleViolation("This permission was already taken back.")
        grant.revoke()
        self._grants.update(grant)
        self._audit.record(actor.id, "permission_revoked", f"user:{grant.user_id}",
                           {"capability": grant.capability})
