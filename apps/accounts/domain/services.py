from apps.core.domain.errors import Forbidden

from .capabilities import Capability, CapabilityCatalog
from .entities import UserAccount
from .policies import PolicyRegistry
from .repositories import GrantRepository


class Authorizer:
    """Answers "may this person do this?" from their role and any granted permissions.
    Every use case that needs a right asks here, so the rule lives in one place."""

    def __init__(self, policies: PolicyRegistry, grants: GrantRepository,
                 catalog: CapabilityCatalog):
        self._policies = policies
        self._grants = grants
        self._catalog = catalog

    def capabilities_of(self, account: UserAccount) -> frozenset[Capability]:
        if account.role is None or not account.is_active:
            return frozenset()
        policy = self._policies.for_role(account.role)
        granted = []
        if policy.accepts_grants:
            for grant in self._grants.list(user_id=account.id):
                capability = self._catalog.find(grant.capability)
                if capability is not None:
                    granted.append(capability)
        return policy.capabilities(granted)

    def can(self, account: UserAccount, capability: Capability) -> bool:
        return capability in self.capabilities_of(account)

    def require(self, account: UserAccount, capability: Capability) -> None:
        if not self.can(account, capability):
            raise Forbidden()

    def require_any(self, account: UserAccount, *capabilities: Capability) -> None:
        held = self.capabilities_of(account)
        if not any(capability in held for capability in capabilities):
            raise Forbidden()
