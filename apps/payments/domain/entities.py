from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from apps.core.domain.entity import Entity
from apps.core.domain.errors import RuleViolation
from apps.core.domain.money import ZERO, Money


def _invalid(field_name: str, message: str) -> RuleViolation:
    return RuleViolation(message, errors={field_name: [message]})


@dataclass(frozen=True, order=True)
class PayMonth:
    """A calendar month, such as 2026-10."""

    year: int
    month: int

    @classmethod
    def parse(cls, text: str) -> "PayMonth":
        try:
            year, month = (int(part) for part in text.split("-"))
            if not (1 <= month <= 12 and 2000 <= year <= 2200):
                raise ValueError
        except ValueError:
            raise _invalid("month", "Use the form YYYY-MM, such as 2026-10.")
        return cls(year, month)

    @classmethod
    def of(cls, day: date) -> "PayMonth":
        return cls(day.year, day.month)

    @property
    def first_day(self) -> date:
        return date(self.year, self.month, 1)

    def following(self) -> "PayMonth":
        return PayMonth(self.year + 1, 1) if self.month == 12 else PayMonth(self.year, self.month + 1)

    def through(self, last: "PayMonth") -> list["PayMonth"]:
        months, current = [], self
        while current <= last:
            months.append(current)
            current = current.following()
        return months

    def __str__(self) -> str:
        return f"{self.year}-{self.month:02d}"


class PaymentKind(StrEnum):
    SALARY = "salary"
    FUEL_BILL = "fuel_bill"


class PaymentMode(StrEnum):
    CASH = "cash"
    BANK = "bank"
    UPI = "upi"


@dataclass(eq=False, kw_only=True)
class SalaryRate(Entity):
    """A person's monthly salary from a month onwards. Earlier months keep the rate that
    was in force then."""

    person_id: UUID
    amount: Decimal
    effective_from: PayMonth
    set_by_id: UUID | None = None

    @classmethod
    def set(cls, *, person_id: UUID, amount, effective_from: PayMonth,
            set_by_id: UUID) -> "SalaryRate":
        return cls(person_id=person_id, effective_from=effective_from, set_by_id=set_by_id,
                   amount=Money.parse(amount, field="amount", allow_zero=True))


@dataclass(eq=False, kw_only=True)
class Payment(Entity):
    """Money paid to a teacher or staff member, towards a month's salary or a fuel bill."""

    NOTE_MAX = 200

    person_id: UUID
    kind: PaymentKind
    amount: Decimal
    paid_on: date
    mode: PaymentMode
    paid_by_id: UUID | None = None
    note: str = ""
    month: PayMonth | None = None
    fuel_bill_id: UUID | None = None
    receipt_number: int | None = None
    # Filled in when read, so the app can show them.
    person_name: str = ""
    role: str = ""

    @classmethod
    def record(cls, *, person_id: UUID, kind: PaymentKind, amount, paid_on: date,
               mode: PaymentMode, paid_by_id: UUID, note: str, month: PayMonth | None,
               fuel_bill_id: UUID | None) -> "Payment":
        note = note.strip()
        if len(note) > cls.NOTE_MAX:
            raise _invalid("note", f"Up to {cls.NOTE_MAX} characters.")
        return cls(person_id=person_id, kind=kind, amount=Money.parse(amount, field="amount"),
                   paid_on=paid_on, mode=mode, paid_by_id=paid_by_id, note=note, month=month,
                   fuel_bill_id=fuel_bill_id)

    @property
    def receipt_no(self) -> str:
        return f"P-{self.receipt_number:06d}" if self.receipt_number else ""


# ------------------------------------------------------------ what is owed
@dataclass(frozen=True)
class BalanceLine:
    due: Decimal
    paid: Decimal

    @property
    def balance(self) -> Decimal:
        return self.due - self.paid


@dataclass(frozen=True)
class MonthLine(BalanceLine):
    month: PayMonth


@dataclass(frozen=True)
class FuelLine(BalanceLine):
    bill_id: UUID
    billed_on: date
    van_name: str


@dataclass(frozen=True)
class Statement:
    """What a person is owed and has been paid: each month's salary and each approved
    fuel bill."""

    person_id: UUID
    salary: list[MonthLine] = field(default_factory=list)
    fuel: list[FuelLine] = field(default_factory=list)

    @property
    def total_due(self) -> Decimal:
        return sum((line.due for line in (*self.salary, *self.fuel)), ZERO)

    @property
    def total_paid(self) -> Decimal:
        return sum((line.paid for line in (*self.salary, *self.fuel)), ZERO)

    @property
    def balance(self) -> Decimal:
        return self.total_due - self.total_paid

    @property
    def salary_balance(self) -> Decimal:
        return sum((line.balance for line in self.salary), ZERO)

    @property
    def fuel_balance(self) -> Decimal:
        return sum((line.balance for line in self.fuel), ZERO)


@dataclass(frozen=True)
class PayeeSummary:
    person_id: UUID
    name: str
    role: str
    current_salary: Decimal | None
    statement: Statement
