from uuid import UUID

from apps.accounts.domain.capabilities import SUBMIT_FUEL_BILL, ALLOT_VANS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import Van
from ..repositories import StaffRepository, VanRepository
from ..services import FleetScope


class ListVans(UseCase):
    """The Principal sees every van; a driver sees the van they drive."""

    def __init__(self, vans: VanRepository, scope: FleetScope, authorizer: Authorizer):
        self._vans = vans
        self._scope = scope
        self._authorizer = authorizer

    def call(self, actor: UserAccount) -> list[Van]:
        if self._scope.sees_all(actor):
            return self._vans.list()
        self._authorizer.require(actor, SUBMIT_FUEL_BILL)
        return self._vans.list(driver_id=actor.id)


class _VanWriter(UseCase):
    def __init__(self, vans: VanRepository, staff: StaffRepository, authorizer: Authorizer,
                 audit: AuditLogger):
        self._vans = vans
        self._staff = staff
        self._authorizer = authorizer
        self._audit = audit

    def _existing(self, van_id: UUID) -> Van:
        van = self._vans.get(van_id)
        if van is None or not van.is_active:
            raise NotFound("This van was not found.")
        return van

    def _ensure_name_free(self, van: Van) -> None:
        twin = self._vans.find_active_by_name(van.name)
        if twin is not None and twin.id != van.id:
            message = f"A van named {van.name} already exists."
            raise RuleViolation(message, errors={"name": [message]})

    def _ensure_driver_ok(self, van: Van) -> None:
        if van.driver_id is None:
            return
        driver = self._staff.get(van.driver_id)
        if driver is None or not driver.is_active:
            raise RuleViolation("This staff member was not found.",
                                errors={"driver_id": ["Choose a staff member."]})
        other = self._vans.find_driven_by(van.driver_id)
        if other is not None and other.id != van.id:
            message = f"{driver.name} already drives {other.name}."
            raise RuleViolation(message, errors={"driver_id": [message]})


class AddVan(_VanWriter):
    def call(self, actor: UserAccount, *, name: str, driver_id: UUID | None = None) -> Van:
        self._authorizer.require(actor, ALLOT_VANS)
        van = Van.create(name=name, driver_id=driver_id)
        self._ensure_name_free(van)
        self._ensure_driver_ok(van)
        saved = self._vans.add(van)
        self._audit.record(actor.id, "van_added", f"van:{saved.id}",
                           {"name": saved.name, "driver": saved.driver_name})
        return saved


class UpdateVan(_VanWriter):
    """Renames the van and/or allots its driver. `changes` holds only what to change, from
    `name` and `driver_id` (None takes the van back from its driver)."""

    ALLOWED = {"name", "driver_id"}

    def call(self, actor: UserAccount, van_id: UUID, **changes) -> Van:
        self._authorizer.require(actor, ALLOT_VANS)
        if not changes or not set(changes) <= self.ALLOWED:
            raise RuleViolation("Nothing to change.")
        van = self._existing(van_id)
        if "name" in changes:
            van.rename(changes["name"])
            self._ensure_name_free(van)
        if "driver_id" in changes:
            van.assign_driver(changes["driver_id"])
            self._ensure_driver_ok(van)
        saved = self._vans.update(van)
        self._audit.record(actor.id, "van_updated", f"van:{saved.id}",
                           {"name": saved.name, "driver": saved.driver_name})
        return saved


class RemoveVan(_VanWriter):
    """Stops using the van. Its fuel bills stay."""

    def call(self, actor: UserAccount, van_id: UUID) -> None:
        self._authorizer.require(actor, ALLOT_VANS)
        van = self._existing(van_id)
        van.remove()
        van.assign_driver(None)
        self._vans.update(van)
        self._audit.record(actor.id, "van_removed", f"van:{van_id}", {"name": van.name})
