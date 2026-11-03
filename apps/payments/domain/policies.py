"""Who can be paid, by whom, and for what. A kind of person is a class; a new one is a
new class."""
from abc import ABC, abstractmethod
from collections.abc import Iterable
from uuid import UUID

from apps.accounts.domain.capabilities import (
    MANAGE_STAFF_PAYMENTS,
    MANAGE_TEACHER_PAYMENTS,
    Capability,
)
from apps.accounts.domain.entities import Role
from apps.core.domain.errors import RuleViolation

from .entities import FuelLine, MonthLine, PayMonth, PaymentKind, Statement


class PayableKind(ABC):
    """One thing money can be paid towards. It finds the line a payment belongs to and
    says which references the payment carries."""

    kind: PaymentKind

    @abstractmethod
    def locate(self, statement: Statement, *, month: PayMonth | None,
               fuel_bill_id: UUID | None):
        """The line to pay towards; raises if the payment does not point at a real one."""


class SalaryKind(PayableKind):
    kind = PaymentKind.SALARY

    def locate(self, statement: Statement, *, month: PayMonth | None,
               fuel_bill_id: UUID | None) -> MonthLine:
        if month is None:
            raise RuleViolation("Give the month.", errors={"month": ["Required."]})
        for line in statement.salary:
            if line.month == month:
                return line
        message = f"No salary is due for {month}."
        raise RuleViolation(message, errors={"month": [message]})


class FuelBillKind(PayableKind):
    kind = PaymentKind.FUEL_BILL

    def locate(self, statement: Statement, *, month: PayMonth | None,
               fuel_bill_id: UUID | None) -> FuelLine:
        if fuel_bill_id is None:
            raise RuleViolation("Give the fuel bill.", errors={"fuel_bill_id": ["Required."]})
        for line in statement.fuel:
            if line.bill_id == fuel_bill_id:
                return line
        message = "This is not an approved fuel bill of this person."
        raise RuleViolation(message, errors={"fuel_bill_id": [message]})


class PayableKinds:
    def __init__(self, kinds: Iterable[PayableKind]):
        self._by_kind = {k.kind: k for k in kinds}

    def for_kind(self, kind: PaymentKind) -> PayableKind:
        return self._by_kind[kind]

    @classmethod
    def default(cls) -> "PayableKinds":
        return cls([SalaryKind(), FuelBillKind()])


class PayeePolicy(ABC):
    role: Role
    manage_right: Capability
    kinds: frozenset[PaymentKind]

    def allows(self, kind: PaymentKind) -> bool:
        return kind in self.kinds


class TeacherPayeePolicy(PayeePolicy):
    role = Role.TEACHER
    manage_right = MANAGE_TEACHER_PAYMENTS
    kinds = frozenset({PaymentKind.SALARY})


class StaffPayeePolicy(PayeePolicy):
    role = Role.STAFF
    manage_right = MANAGE_STAFF_PAYMENTS
    kinds = frozenset({PaymentKind.SALARY, PaymentKind.FUEL_BILL})


class PayeePolicies:
    def __init__(self, policies: Iterable[PayeePolicy]):
        self._by_role = {p.role: p for p in policies}

    def all(self) -> list[PayeePolicy]:
        return list(self._by_role.values())

    def for_role(self, role: Role | None) -> PayeePolicy:
        policy = self._by_role.get(role)
        if policy is None:
            raise RuleViolation("Only teachers and staff are paid here.",
                                errors={"person_id": ["Choose a teacher or staff member."]})
        return policy

    @classmethod
    def default(cls) -> "PayeePolicies":
        return cls([TeacherPayeePolicy(), StaffPayeePolicy()])
