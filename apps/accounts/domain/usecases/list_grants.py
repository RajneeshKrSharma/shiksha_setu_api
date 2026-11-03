from uuid import UUID

from apps.core.domain.usecase import UseCase

from ..capabilities import GRANT_PERMISSIONS
from ..entities import PermissionGrant, UserAccount
from ..repositories import GrantRepository
from ..services import Authorizer


class ListGrants(UseCase):
    def __init__(self, grants: GrantRepository, authorizer: Authorizer):
        self._grants = grants
        self._authorizer = authorizer

    def call(self, actor: UserAccount, *, user_id: UUID | None = None) -> list[PermissionGrant]:
        self._authorizer.require(actor, GRANT_PERMISSIONS)
        return self._grants.list(user_id=user_id, active_only=True)
