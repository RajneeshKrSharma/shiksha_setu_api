from rest_framework.permissions import SAFE_METHODS, BasePermission

from config.container import container

from ..domain.capabilities import Capability


class RequiresCapability(BasePermission):
    """Role checks live on the server, never trusted from the app. The use case
    checks again, so a route that forgets this is still safe."""

    capability: Capability | None = None

    @classmethod
    def of(cls, capability: Capability) -> type["RequiresCapability"]:
        return type(f"Requires_{capability.code}", (cls,), {"capability": capability})

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return container.authorizer().can(container.actor(user), self.capability)


class CapabilityGate(BasePermission):
    """Reading needs any one of the `read` capabilities, changing needs any one of
    the `write` capabilities."""

    read: tuple[Capability, ...] = ()
    write: tuple[Capability, ...] = ()

    @classmethod
    def of(cls, *, read, write) -> type["CapabilityGate"]:
        return type("CapabilityGateOf", (cls,), {"read": tuple(read), "write": tuple(write)})

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        needed = self.read if request.method in SAFE_METHODS else self.write
        authorizer, actor = container.authorizer(), container.actor(user)
        return any(authorizer.can(actor, capability) for capability in needed)


class ReadByAnyoneWriteWith(RequiresCapability):
    """Every signed-in person may read; only those holding the capability may change."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return super().has_permission(request, view)
