from datetime import date
from uuid import UUID

from apps.accounts.domain.entities import UserAccount
from apps.core.domain.audit import AuditLogger
from apps.core.domain.clock import Clock
from apps.core.domain.errors import RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import PayMonth, Payment, PaymentKind, PaymentMode
from ..policies import PayableKinds
from ..repositories import PaymentRepository
from ..services import PayeeAccess, StatementBuilder


class RecordPayment(UseCase):
    """The Principal records money paid to a teacher or staff member towards one month's
    salary or one approved fuel bill. It can be part of what is due (an instalment) but
    never more."""

    def __init__(self, payments: PaymentRepository, statements: StatementBuilder,
                 access: PayeeAccess, kinds: PayableKinds, audit: AuditLogger, clock: Clock):
        self._payments = payments
        self._statements = statements
        self._access = access
        self._kinds = kinds
        self._audit = audit
        self._clock = clock

    def call(self, actor: UserAccount, person_id: UUID, *, kind: PaymentKind, amount,
             mode: PaymentMode, paid_on: date | None = None, note: str = "",
             month: PayMonth | None = None, fuel_bill_id: UUID | None = None) -> Payment:
        person, policy = self._access.payee(person_id)
        self._access.require_manage(actor, policy)
        if not policy.allows(kind):
            message = f"{person.name} cannot be paid for {kind.value.replace('_', ' ')}."
            raise RuleViolation(message, errors={"kind": [message]})

        today = self._clock.today()
        payment = Payment.record(
            person_id=person_id, kind=kind, amount=amount, paid_on=paid_on or today, mode=mode,
            paid_by_id=actor.id, note=note, month=month, fuel_bill_id=fuel_bill_id,
        )
        line = self._kinds.for_kind(kind).locate(
            self._statements.build(person_id, today), month=month, fuel_bill_id=fuel_bill_id
        )
        if line.balance <= 0:
            raise RuleViolation("Nothing is left to pay here.", errors={"amount": ["Already paid."]})
        if payment.amount > line.balance:
            message = f"Only {line.balance} is left to pay here."
            raise RuleViolation(message, errors={"amount": [message]})

        saved = self._payments.add(payment)
        self._audit.record(actor.id, "payment_made", f"user:{person_id}", {
            "kind": kind.value, "amount": str(saved.amount), "receipt": saved.receipt_no,
            "mode": mode.value,
        })
        return saved


class ListPayments(UseCase):
    """The Principal sees payments of the people they manage; a teacher or staff member sees
    their own."""

    def __init__(self, payments: PaymentRepository, access: PayeeAccess):
        self._payments = payments
        self._access = access

    def call(self, actor: UserAccount, *, person_id: UUID | None = None,
             from_date: date | None = None, to_date: date | None = None) -> list[Payment]:
        if person_id is not None:
            person, policy = self._access.payee(person_id)
            self._access.require_view(actor, person, policy)
            return self._payments.list(person_id=person_id, from_date=from_date, to_date=to_date)
        managed = {policy.role.value for policy in self._access.managed_roles(actor)}
        found = self._payments.list(from_date=from_date, to_date=to_date)
        return [p for p in found if p.role in managed or p.person_id == actor.id]
