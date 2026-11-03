from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from apps.accounts.domain.capabilities import MANAGE_FEES
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.clock import Clock
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.money import Money
from apps.core.domain.usecase import UseCase

from ..entities import Student
from ..fees import FeeHead, FeePayment, FeeStatement, HeadPolicies
from ..repositories import (
    ClassRepository,
    FeePaymentRepository,
    FeeStructureRepository,
    StudentRepository,
)
from ..services import StatementBuilder


@dataclass(frozen=True)
class StructureLine:
    head: FeeHead
    amount: Decimal | None  # None: not set for this class yet


@dataclass(frozen=True)
class StudentFees:
    statement: FeeStatement
    payments: list[FeePayment]


class _FeeUseCase(UseCase):
    def __init__(self, authorizer: Authorizer):
        self._authorizer = authorizer

    def _require(self, actor: UserAccount) -> None:
        self._authorizer.require(actor, MANAGE_FEES)


class GetFeeStructure(_FeeUseCase):
    def __init__(self, classes: ClassRepository, structure: FeeStructureRepository,
                 policies: HeadPolicies, authorizer: Authorizer):
        super().__init__(authorizer)
        self._classes = classes
        self._structure = structure
        self._policies = policies

    def call(self, actor: UserAccount, class_id: UUID) -> list[StructureLine]:
        self._require(actor)
        if self._classes.get(class_id) is None:
            raise NotFound("This class was not found.")
        amounts = self._structure.amounts_for(class_id)
        return [
            StructureLine(policy.head, amounts.get(policy.head))
            for policy in self._policies.all() if policy.settable
        ]


class SetFeeAmount(_FeeUseCase):
    """The Principal's amount for one fee in one class. Dress and books are not set
    here: they are charged from the items sold."""

    def __init__(self, classes: ClassRepository, structure: FeeStructureRepository,
                 policies: HeadPolicies, authorizer: Authorizer, audit: AuditLogger):
        super().__init__(authorizer)
        self._classes = classes
        self._structure = structure
        self._policies = policies
        self._audit = audit

    def call(self, actor: UserAccount, class_id: UUID, head: FeeHead, amount) -> Decimal:
        self._require(actor)
        if not self._policies.for_head(head).settable:
            raise RuleViolation(
                f"{head.label} is charged from the items sold, not from a fixed amount.",
                errors={"head": ["This fee has no fixed amount."]},
            )
        school_class = self._classes.get(class_id)
        if school_class is None or not school_class.is_active:
            raise NotFound("This class was not found.")
        amount = Money.parse(amount, field="amount", allow_zero=True)
        self._structure.set_amount(class_id, head, amount)
        self._audit.record(actor.id, "fee_amount_set", f"class:{class_id}",
                           {"head": head.value, "amount": str(amount)})
        return amount


class _StatementUseCase(_FeeUseCase):
    def __init__(self, students: StudentRepository, statements: StatementBuilder,
                 authorizer: Authorizer):
        super().__init__(authorizer)
        self._students = students
        self._statements = statements

    def _student(self, student_id: UUID) -> Student:
        student = self._students.get(student_id)
        if student is None:
            raise NotFound("This student was not found.")
        return student


class ListFeeAccounts(_StatementUseCase):
    def call(self, actor: UserAccount, *, class_id: UUID | None = None, query: str = "",
             only_due: bool = False) -> list[FeeStatement]:
        self._require(actor)
        students = self._students.list(query=query.strip(), active=True, class_id=class_id)
        statements = [self._statements.build(student) for student in students]
        return [s for s in statements if s.balance > 0] if only_due else statements


class GetStudentFees(_StatementUseCase):
    def __init__(self, students: StudentRepository, statements: StatementBuilder,
                 payments: FeePaymentRepository, authorizer: Authorizer):
        super().__init__(students, statements, authorizer)
        self._payments = payments

    def call(self, actor: UserAccount, student_id: UUID) -> StudentFees:
        self._require(actor)
        student = self._student(student_id)
        return StudentFees(self._statements.build(student),
                           self._payments.list(student_id=student_id))


class ReceiveFeePayment(_StatementUseCase):
    """Money taken from a student for one fee. It can be less than what is due (an
    instalment) but never more."""

    def __init__(self, students: StudentRepository, statements: StatementBuilder,
                 payments: FeePaymentRepository, authorizer: Authorizer, audit: AuditLogger,
                 clock: Clock):
        super().__init__(students, statements, authorizer)
        self._payments = payments
        self._audit = audit
        self._clock = clock

    def call(self, actor: UserAccount, *, student_id: UUID, head: FeeHead, amount,
             paid_on: date | None = None, note: str = "") -> FeePayment:
        self._require(actor)
        student = self._student(student_id)
        payment = FeePayment.receive(
            student_id=student_id, head=head, amount=amount,
            paid_on=paid_on or self._clock.today(), received_by_id=actor.id, note=note,
        )
        balance = self._statements.build(student).line(head).balance
        if balance <= 0:
            message = f"Nothing is due for {head.label}."
            raise RuleViolation(message, errors={"head": [message]})
        if payment.amount > balance:
            message = f"Only {balance} is due for {head.label}."
            raise RuleViolation(message, errors={"amount": [message]})
        saved = self._payments.add(payment)
        self._audit.record(actor.id, "fee_payment_received", f"student:{student_id}", {
            "head": head.value, "amount": str(saved.amount), "receipt": saved.receipt_no,
        })
        return saved


class ListFeePayments(_FeeUseCase):
    def __init__(self, payments: FeePaymentRepository, authorizer: Authorizer):
        super().__init__(authorizer)
        self._payments = payments

    def call(self, actor: UserAccount, *, student_id: UUID | None = None,
             from_date: date | None = None, to_date: date | None = None) -> list[FeePayment]:
        self._require(actor)
        return self._payments.list(student_id=student_id, from_date=from_date, to_date=to_date)
