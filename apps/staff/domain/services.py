from uuid import UUID

from apps.accounts.domain.capabilities import ALLOT_VANS, APPROVE_FUEL_BILLS, MANAGE_STAFF
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.errors import RuleViolation

from .fuel import FuelBill, FuelEstimator, FuelReport
from .repositories import FuelBillRepository, VanRepository


class FleetScope:
    """Those who run the staff and vans see everything; a staff member sees only their
    own van and bills."""

    def __init__(self, authorizer: Authorizer):
        self._authorizer = authorizer

    def sees_all(self, actor: UserAccount) -> bool:
        held = self._authorizer.capabilities_of(actor)
        return bool(held & {ALLOT_VANS, MANAGE_STAFF, APPROVE_FUEL_BILLS})


class DrivingRule:
    """A person who drives a van cannot be removed until the van has another driver."""

    def __init__(self, vans: VanRepository):
        self._vans = vans

    def ensure_not_driving(self, staff_id: UUID) -> None:
        van = self._vans.find_driven_by(staff_id)
        if van is not None:
            raise RuleViolation(
                f"{van.name} is driven by this person. Change the van's driver first.",
                errors={"is_active": ["Drives a van."]},
            )


class FuelReporter:
    """Adds the distance and mileage estimate to bills."""

    def __init__(self, bills: FuelBillRepository, estimator: FuelEstimator):
        self._bills = bills
        self._estimator = estimator

    def report(self, bill: FuelBill) -> FuelReport:
        previous = self._bills.previous_by_odometer(bill.van_id, bill.odometer_km, bill.id)
        return self._estimator.report(bill, previous)
