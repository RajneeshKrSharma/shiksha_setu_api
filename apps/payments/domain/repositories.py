from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from uuid import UUID

from .entities import PayMonth, Payment, PaymentKind, SalaryRate


class SalaryRepository(ABC):
    @abstractmethod
    def history(self, person_id: UUID) -> list[SalaryRate]:
        """Newest first."""

    @abstractmethod
    def save(self, rate: SalaryRate) -> SalaryRate:
        """Adds the rate, or replaces the person's rate that starts in the same month."""


class PaymentRepository(ABC):
    """Payments are never edited, so there is no update. The repository gives each one
    its receipt number."""

    @abstractmethod
    def add(self, payment: Payment) -> Payment: ...

    @abstractmethod
    def list(self, *, person_id: UUID | None = None, from_date: date | None = None,
             to_date: date | None = None) -> list[Payment]:
        """Newest first."""

    @abstractmethod
    def paid_by_month(self, person_id: UUID) -> dict[PayMonth, Decimal]: ...

    @abstractmethod
    def paid_by_fuel_bill(self, person_id: UUID) -> dict[UUID, Decimal]: ...

    @abstractmethod
    def paid_out_by_month(self, from_date: date, to_date: date
                          ) -> dict[date, dict[PaymentKind, Decimal]]:
        """What was paid out in each month (keyed by its first day), by kind."""

    @abstractmethod
    def has_salary_payment_from(self, person_id: UUID, month: PayMonth) -> bool:
        """Whether a salary payment exists for this month or any later one."""
