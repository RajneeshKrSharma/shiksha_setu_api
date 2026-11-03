from apps.core.domain.usecase import UseCase

from ..capabilities import Capability, CapabilityCatalog


class ListCapabilities(UseCase):
    """The permissions the Principal can choose from when giving one to the Vice Principal."""

    def __init__(self, catalog: CapabilityCatalog):
        self._catalog = catalog

    def call(self) -> list[Capability]:
        return self._catalog.grantable()
