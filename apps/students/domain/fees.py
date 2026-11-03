"""What a student owes and has paid. Each fee head is a small class that knows where
its amount comes from, so a new head is a new class and nothing else changes."""
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from apps.core.domain.entity import Entity
from apps.core.domain.errors import RuleViolation
from apps.core.domain.money import ZERO, Money

from .accessories import AccessoryKind
from .entities import Student


class FeeHead(StrEnum):
    TUITION = "tuition"
    VAN = "van"
    DRESS = "dress"
    BOOKS = "books"

    @property
    def label(self) -> str:
        return self.value.title()


@dataclass(frozen=True)
class FeeContext:
    """What the policies need to know about one student."""

    amounts: dict[FeeHead, Decimal]  # set per class by the Principal
    sold: dict[AccessoryKind, Decimal]  # total of items sold to the student


class HeadPolicy(ABC):
    head: FeeHead
    # True: the Principal sets this head's amount for each class.
    settable = False

    @abstractmethod
    def due(self, student: Student, context: FeeContext) -> Decimal: ...


class StructureHeadPolicy(HeadPolicy):
    settable = True

    def due(self, student: Student, context: FeeContext) -> Decimal:
        return context.amounts.get(self.head, ZERO)


class TuitionPolicy(StructureHeadPolicy):
    head = FeeHead.TUITION


class VanPolicy(StructureHeadPolicy):
    head = FeeHead.VAN

    def due(self, student: Student, context: FeeContext) -> Decimal:
        return super().due(student, context) if student.uses_van else ZERO


class ItemHeadPolicy(HeadPolicy):
    """Owed is whatever was sold to the student of this kind."""

    kind: AccessoryKind

    def due(self, student: Student, context: FeeContext) -> Decimal:
        return context.sold.get(self.kind, ZERO)


class DressPolicy(ItemHeadPolicy):
    head = FeeHead.DRESS
    kind = AccessoryKind.DRESS


class BooksPolicy(ItemHeadPolicy):
    head = FeeHead.BOOKS
    kind = AccessoryKind.BOOKS


class HeadPolicies:
    def __init__(self, policies: Iterable[HeadPolicy]):
        self._by_head = {policy.head: policy for policy in policies}

    def all(self) -> list[HeadPolicy]:
        return list(self._by_head.values())

    def for_head(self, head: FeeHead) -> HeadPolicy:
        policy = self._by_head.get(head)
        if policy is None:
            raise RuleViolation("This fee does not exist.", errors={"head": ["Unknown fee."]})
        return policy

    @classmethod
    def default(cls) -> "HeadPolicies":
        return cls([TuitionPolicy(), VanPolicy(), DressPolicy(), BooksPolicy()])


@dataclass(frozen=True)
class HeadLine:
    head: FeeHead
    due: Decimal
    paid: Decimal

    @property
    def balance(self) -> Decimal:
        return self.due - self.paid


@dataclass(frozen=True)
class FeeStatement:
    student: Student
    lines: list[HeadLine] = field(default_factory=list)

    @property
    def total_due(self) -> Decimal:
        return sum((line.due for line in self.lines), ZERO)

    @property
    def total_paid(self) -> Decimal:
        return sum((line.paid for line in self.lines), ZERO)

    @property
    def balance(self) -> Decimal:
        return self.total_due - self.total_paid

    def line(self, head: FeeHead) -> HeadLine:
        return next(line for line in self.lines if line.head == head)


class FeeCalculator:
    def __init__(self, policies: HeadPolicies):
        self._policies = policies

    def statement(self, student: Student, context: FeeContext,
                  paid: dict[FeeHead, Decimal]) -> FeeStatement:
        return FeeStatement(student, [
            HeadLine(policy.head, policy.due(student, context), paid.get(policy.head, ZERO))
            for policy in self._policies.all()
        ])


@dataclass(eq=False, kw_only=True)
class FeePayment(Entity):
    NOTE_MAX = 200

    student_id: UUID
    head: FeeHead
    amount: Decimal
    paid_on: date
    received_by_id: UUID | None = None
    note: str = ""
    receipt_number: int | None = None

    @classmethod
    def receive(cls, *, student_id: UUID, head: FeeHead, amount, paid_on: date,
                received_by_id: UUID, note: str = "") -> "FeePayment":
        note = note.strip()
        if len(note) > cls.NOTE_MAX:
            message = f"Up to {cls.NOTE_MAX} characters."
            raise RuleViolation(message, errors={"note": [message]})
        return cls(student_id=student_id, head=head, paid_on=paid_on,
                   amount=Money.parse(amount, field="amount"),
                   received_by_id=received_by_id, note=note)

    @property
    def receipt_no(self) -> str:
        return f"R-{self.receipt_number:06d}" if self.receipt_number else ""
