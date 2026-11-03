from dataclasses import dataclass

from apps.core.domain.usecase import UseCase

from ..capabilities import Capability
from ..entities import UserAccount
from ..services import Authorizer


@dataclass(frozen=True)
class CurrentUser:
    account: UserAccount
    capabilities: list[Capability]


class GetCurrentUser(UseCase):
    """The signed-in person and what they may do, so the app shows only their screens."""

    def __init__(self, authorizer: Authorizer):
        self._authorizer = authorizer

    def call(self, actor: UserAccount) -> CurrentUser:
        capabilities = sorted(self._authorizer.capabilities_of(actor), key=lambda c: c.code)
        return CurrentUser(account=actor, capabilities=capabilities)
