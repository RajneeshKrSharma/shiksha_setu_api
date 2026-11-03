from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from uuid import UUID

from apps.core.domain.entity import Entity
from apps.core.domain.errors import RuleViolation
from apps.core.domain.money import ZERO, Money, Quantity


def _invalid(field: str, message: str) -> RuleViolation:
    return RuleViolation(message, errors={field: [message]})


class FuelType(StrEnum):
    PETROL = "petrol"
    DIESEL = "diesel"


class BillStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


@dataclass(eq=False, kw_only=True)
class FuelBill(Entity):
    """A fuel fill-up for a van. The amount is litres times rate. The odometer reading
    is what lets the school estimate the distance covered."""

    LITRES_MAX = Decimal("1000.00")
    ODOMETER_MAX = 9_999_999
    REASON_MAX = 300

    van_id: UUID
    submitted_by_id: UUID
    billed_on: date
    fuel: FuelType
    litres: Decimal
    rate: Decimal
    odometer_km: int
    # Who the bill's amount is paid to: the driver.
    payee_id: UUID | None = None
    status: BillStatus = BillStatus.PENDING
    decided_by_id: UUID | None = None
    decided_on: date | None = None
    reject_reason: str = ""
    # Filled in when read, so the app can show them.
    van_name: str = ""
    submitted_by_name: str = ""
    decided_by_name: str = ""

    @classmethod
    def submit(cls, *, van_id: UUID, submitted_by_id: UUID, payee_id: UUID | None,
               billed_on: date, today: date, fuel: FuelType, litres, rate,
               odometer_km: int) -> "FuelBill":
        if billed_on > today:
            raise _invalid("billed_on", "A bill cannot be dated in the future.")
        if not 1 <= odometer_km <= cls.ODOMETER_MAX:
            raise _invalid("odometer_km", f"Between 1 and {cls.ODOMETER_MAX}.")
        return cls(
            van_id=van_id, submitted_by_id=submitted_by_id, payee_id=payee_id,
            billed_on=billed_on, fuel=fuel,
            litres=Quantity.parse(litres, field="litres", maximum=cls.LITRES_MAX),
            rate=Money.parse(rate, field="rate"), odometer_km=odometer_km,
        )

    @property
    def amount(self) -> Decimal:
        return (self.litres * self.rate).quantize(ZERO, rounding=ROUND_HALF_UP)

    @property
    def counts(self) -> bool:
        """Pending and approved bills count towards the van's odometer history."""
        return self.status in (BillStatus.PENDING, BillStatus.APPROVED)

    def approve(self, *, by_id: UUID, on: date) -> None:
        self._decide(BillStatus.APPROVED, by_id, on, "")

    def reject(self, *, by_id: UUID, on: date, reason: str) -> None:
        reason = reason.strip()
        if not reason or len(reason) > self.REASON_MAX:
            raise _invalid("reason", f"A reason is required, up to {self.REASON_MAX} characters.")
        self._decide(BillStatus.REJECTED, by_id, on, reason)

    def withdraw(self) -> None:
        self._require_pending()
        self.status = BillStatus.WITHDRAWN

    def _decide(self, status: BillStatus, by_id: UUID, on: date, reason: str) -> None:
        self._require_pending()
        self.status, self.decided_by_id, self.decided_on = status, by_id, on
        self.reject_reason = reason

    def _require_pending(self) -> None:
        if self.status != BillStatus.PENDING:
            raise RuleViolation(f"This bill is already {self.status.value}.")


@dataclass(frozen=True)
class FuelReport:
    """A bill with the estimate worked out from the van's previous fill-up."""

    bill: FuelBill
    distance_km: int | None
    km_per_litre: Decimal | None


class FuelEstimator:
    """Distance is this bill's odometer minus the previous fill-up's. Mileage is that
    distance over the litres filled now (the fill replaces what the distance used)."""

    def report(self, bill: FuelBill, previous: FuelBill | None) -> FuelReport:
        if previous is None:
            return FuelReport(bill, None, None)
        distance = bill.odometer_km - previous.odometer_km
        per_litre = (Decimal(distance) / bill.litres).quantize(ZERO, rounding=ROUND_HALF_UP)
        return FuelReport(bill, distance, per_litre)
