from uuid import UUID

from apps.accounts.domain.entities import UserAccount
from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import PayMonth, SalaryRate
from ..repositories import PaymentRepository, SalaryRepository
from ..services import PayeeAccess


class SetSalary(UseCase):
    """Sets a person's monthly salary from a month onwards. Earlier months keep their old
    amount, and a month that already has payments cannot be changed."""

    def __init__(self, salaries: SalaryRepository, payments: PaymentRepository,
                 access: PayeeAccess, audit: AuditLogger):
        self._salaries = salaries
        self._payments = payments
        self._access = access
        self._audit = audit

    def call(self, actor: UserAccount, person_id: UUID, *, amount,
             effective_from: PayMonth) -> SalaryRate:
        person, policy = self._access.payee(person_id)
        self._access.require_manage(actor, policy)
        if not person.is_active:
            raise RuleViolation("This person is no longer active.")
        if self._payments.has_salary_payment_from(person_id, effective_from):
            message = f"Salary has already been paid for {effective_from} or a later month."
            raise RuleViolation(message, errors={"effective_from": [message]})
        saved = self._salaries.save(SalaryRate.set(
            person_id=person_id, amount=amount, effective_from=effective_from, set_by_id=actor.id
        ))
        self._audit.record(actor.id, "salary_set", f"user:{person_id}", {
            "amount": str(saved.amount), "from": str(effective_from),
        })
        return saved


class GetSalaryHistory(UseCase):
    def __init__(self, salaries: SalaryRepository, access: PayeeAccess):
        self._salaries = salaries
        self._access = access

    def call(self, actor: UserAccount, person_id: UUID) -> list[SalaryRate]:
        person, policy = self._access.payee(person_id)
        self._access.require_view(actor, person, policy)
        return self._salaries.history(person_id)
