from datetime import date
from uuid import UUID

from apps.accounts.domain.capabilities import APPROVE_FUEL_BILLS, SUBMIT_FUEL_BILL
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.clock import Clock
from apps.core.domain.errors import Forbidden, NotFound, RuleViolation
from apps.core.domain.usecase import UseCase

from ..fuel import BillStatus, FuelBill, FuelReport, FuelType
from ..repositories import FuelBillRepository, VanRepository
from ..services import FuelReporter


class SubmitFuelBill(UseCase):
    """A driver submits a bill for their own van. Whoever approves bills may submit for
    any van. The odometer must go up from one bill to the next."""

    def __init__(self, bills: FuelBillRepository, vans: VanRepository,
                 reporter: FuelReporter, authorizer: Authorizer, audit: AuditLogger,
                 clock: Clock):
        self._bills = bills
        self._vans = vans
        self._reporter = reporter
        self._authorizer = authorizer
        self._audit = audit
        self._clock = clock

    def call(self, actor: UserAccount, *, billed_on: date, fuel: FuelType, litres, rate,
             odometer_km: int, van_id: UUID | None = None) -> FuelReport:
        self._authorizer.require(actor, SUBMIT_FUEL_BILL)
        van = self._van_for(actor, van_id)
        # The driver is paid: the submitter for their own van, the van's driver otherwise.
        payee_id = van.driver_id if self._authorizer.can(actor, APPROVE_FUEL_BILLS) else actor.id
        bill = FuelBill.submit(
            van_id=van.id, submitted_by_id=actor.id, payee_id=payee_id, billed_on=billed_on,
            today=self._clock.today(), fuel=fuel, litres=litres, rate=rate,
            odometer_km=odometer_km,
        )
        self._check_odometer(bill)
        saved = self._bills.add(bill)
        self._audit.record(actor.id, "fuel_bill_submitted", f"van:{van.id}", {
            "amount": str(saved.amount), "odometer_km": saved.odometer_km,
        })
        return self._reporter.report(saved)

    def _van_for(self, actor: UserAccount, van_id: UUID | None):
        if self._authorizer.can(actor, APPROVE_FUEL_BILLS):
            if van_id is None:
                raise RuleViolation("Choose the van.", errors={"van_id": ["Required."]})
            van = self._vans.get(van_id)
        else:
            van = self._vans.find_driven_by(actor.id)
            if van is None:
                raise RuleViolation("No van is allotted to you.")
            if van_id not in (None, van.id):
                raise Forbidden("You can submit bills only for your own van.")
        if van is None or not van.is_active:
            raise NotFound("This van was not found.")
        return van

    def _check_odometer(self, bill: FuelBill) -> None:
        before = self._bills.highest_odometer_up_to(bill.van_id, bill.billed_on)
        after = self._bills.lowest_odometer_after(bill.van_id, bill.billed_on)
        if before is not None and bill.odometer_km <= before:
            message = f"The odometer must be above {before} km, the van's last reading."
            raise RuleViolation(message, errors={"odometer_km": [message]})
        if after is not None and bill.odometer_km >= after:
            message = f"The odometer must be below {after} km, the van's next reading."
            raise RuleViolation(message, errors={"odometer_km": [message]})


class ListFuelBills(UseCase):
    """A driver sees their own bills; whoever approves bills can see all."""

    def __init__(self, bills: FuelBillRepository, reporter: FuelReporter,
                 authorizer: Authorizer):
        self._bills = bills
        self._reporter = reporter
        self._authorizer = authorizer

    def call(self, actor: UserAccount, *, van_id: UUID | None = None,
             status: BillStatus | None = None, from_date: date | None = None,
             to_date: date | None = None) -> list[FuelReport]:
        submitted_by = None
        if not self._authorizer.can(actor, APPROVE_FUEL_BILLS):
            self._authorizer.require(actor, SUBMIT_FUEL_BILL)
            submitted_by = actor.id
        bills = self._bills.list(van_id=van_id, submitted_by_id=submitted_by, status=status,
                                 from_date=from_date, to_date=to_date)
        return [self._reporter.report(bill) for bill in bills]


class _Decision(UseCase):
    def __init__(self, bills: FuelBillRepository, reporter: FuelReporter,
                 authorizer: Authorizer, audit: AuditLogger, clock: Clock):
        self._bills = bills
        self._reporter = reporter
        self._authorizer = authorizer
        self._audit = audit
        self._clock = clock

    def _pending(self, bill_id: UUID) -> FuelBill:
        bill = self._bills.get(bill_id)
        if bill is None:
            raise NotFound("This bill was not found.")
        return bill


class ApproveFuelBill(_Decision):
    def call(self, actor: UserAccount, bill_id: UUID) -> FuelReport:
        self._authorizer.require(actor, APPROVE_FUEL_BILLS)
        bill = self._pending(bill_id)
        bill.approve(by_id=actor.id, on=self._clock.today())
        saved = self._bills.update(bill)
        self._audit.record(actor.id, "fuel_bill_approved", f"van:{saved.van_id}",
                           {"amount": str(saved.amount)})
        return self._reporter.report(saved)


class RejectFuelBill(_Decision):
    def call(self, actor: UserAccount, bill_id: UUID, *, reason: str) -> FuelReport:
        self._authorizer.require(actor, APPROVE_FUEL_BILLS)
        bill = self._pending(bill_id)
        bill.reject(by_id=actor.id, on=self._clock.today(), reason=reason)
        saved = self._bills.update(bill)
        self._audit.record(actor.id, "fuel_bill_rejected", f"van:{saved.van_id}",
                           {"amount": str(saved.amount), "reason": saved.reject_reason})
        return self._reporter.report(saved)


class WithdrawFuelBill(UseCase):
    """The person who submitted a bill takes it back, while it is still waiting."""

    def __init__(self, bills: FuelBillRepository, authorizer: Authorizer):
        self._bills = bills
        self._authorizer = authorizer

    def call(self, actor: UserAccount, bill_id: UUID) -> None:
        self._authorizer.require(actor, SUBMIT_FUEL_BILL)
        bill = self._bills.get(bill_id)
        if bill is None or bill.submitted_by_id != actor.id:
            raise NotFound("This bill was not found.")
        bill.withdraw()
        self._bills.update(bill)
