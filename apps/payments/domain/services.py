from datetime import date
from decimal import Decimal
from uuid import UUID

from apps.accounts.domain.capabilities import VIEW_OWN_PAYMENTS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.repositories import UserRepository
from apps.accounts.domain.services import Authorizer
from apps.core.domain.errors import Forbidden, NotFound
from apps.core.domain.money import ZERO
from apps.staff.domain.fuel import BillStatus
from apps.staff.domain.repositories import FuelBillRepository

from .entities import FuelLine, MonthLine, PayMonth, SalaryRate, Statement
from .policies import PayeePolicies, PayeePolicy
from .repositories import PaymentRepository, SalaryRepository


class SalaryTimeline:
    """A person's salary rates over time: a month uses the latest rate that started on or
    before it."""

    def __init__(self, rates: list[SalaryRate]):
        self._rates = sorted(rates, key=lambda r: r.effective_from)

    def rate_for(self, month: PayMonth) -> SalaryRate | None:
        current = None
        for rate in self._rates:
            if rate.effective_from <= month:
                current = rate
        return current

    def first_month(self) -> PayMonth | None:
        return self._rates[0].effective_from if self._rates else None


class StatementBuilder:
    """What one person is owed and has been paid, up to today's month."""

    def __init__(self, salaries: SalaryRepository, payments: PaymentRepository,
                 bills: FuelBillRepository):
        self._salaries = salaries
        self._payments = payments
        self._bills = bills

    def timeline(self, person_id: UUID) -> SalaryTimeline:
        return SalaryTimeline(self._salaries.history(person_id))

    def build(self, person_id: UUID, today: date) -> Statement:
        return Statement(
            person_id=person_id,
            salary=self._salary_lines(person_id, today),
            fuel=self._fuel_lines(person_id),
        )

    def _salary_lines(self, person_id: UUID, today: date) -> list[MonthLine]:
        timeline = self.timeline(person_id)
        first = timeline.first_month()
        if first is None:
            return []
        paid = self._payments.paid_by_month(person_id)
        lines = []
        for month in first.through(PayMonth.of(today)):
            rate = timeline.rate_for(month)
            due, got = (rate.amount if rate else ZERO), paid.get(month, ZERO)
            if due or got:
                lines.append(MonthLine(due=due, paid=got, month=month))
        return lines

    def _fuel_lines(self, person_id: UUID) -> list[FuelLine]:
        paid = self._payments.paid_by_fuel_bill(person_id)
        bills = self._bills.list(payee_id=person_id, status=BillStatus.APPROVED)
        return [
            FuelLine(due=bill.amount, paid=paid.get(bill.id, ZERO), bill_id=bill.id,
                     billed_on=bill.billed_on, van_name=bill.van_name)
            for bill in bills
        ]

    def current_salary(self, person_id: UUID, today: date) -> Decimal | None:
        rate = self.timeline(person_id).rate_for(PayMonth.of(today))
        return rate.amount if rate else None


class PayeeAccess:
    """Finds who is being paid and whether the actor may manage or see their payments."""

    def __init__(self, users: UserRepository, policies: PayeePolicies, authorizer: Authorizer):
        self._users = users
        self._policies = policies
        self._authorizer = authorizer

    def payee(self, person_id: UUID) -> tuple[UserAccount, PayeePolicy]:
        person = self._users.get(person_id)
        if person is None:
            raise NotFound("This person was not found.")
        return person, self._policies.for_role(person.role)

    def require_manage(self, actor: UserAccount, policy: PayeePolicy) -> None:
        self._authorizer.require(actor, policy.manage_right)

    def require_view(self, actor: UserAccount, person: UserAccount, policy: PayeePolicy) -> None:
        if self._authorizer.can(actor, policy.manage_right):
            return
        if actor.id == person.id and self._authorizer.can(actor, VIEW_OWN_PAYMENTS):
            return
        raise Forbidden()

    def managed_roles(self, actor: UserAccount) -> list[PayeePolicy]:
        return [p for p in self._policies.all() if self._authorizer.can(actor, p.manage_right)]
