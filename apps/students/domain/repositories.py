from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from uuid import UUID

from apps.core.domain.repository import MemberRepository, Repository

from .accessories import AccessoryIssue, AccessoryItem, AccessoryKind
from .entities import ClassLevel, SchoolClass, Student
from .fees import FeeHead, FeePayment


class ClassRepository(Repository[SchoolClass]):
    @abstractmethod
    def find_active(self, level: ClassLevel, section: str) -> SchoolClass | None: ...

    @abstractmethod
    def list(self, *, active: bool | None = True) -> list[SchoolClass]:
        """Lowest class first, then by section."""


class StudentRepository(MemberRepository[Student]):
    @abstractmethod
    def list(self, *, query: str = "", active: bool | None = None,
             class_id: UUID | None = None) -> list[Student]:
        """By class, then roll number."""

    @abstractmethod
    def find_active_by_roll(self, class_id: UUID, roll_number: str) -> Student | None: ...

    @abstractmethod
    def count_active_in_class(self, class_id: UUID) -> int: ...


class AccessoryItemRepository(Repository[AccessoryItem]):
    @abstractmethod
    def list(self, *, kind: AccessoryKind | None = None, class_id: UUID | None = None,
             active: bool = True) -> list[AccessoryItem]:
        """With a class: that class's items and the ones for every class."""


class AccessoryIssueRepository(ABC):
    """Sales are never edited, so there is no update."""

    @abstractmethod
    def add(self, issue: AccessoryIssue) -> AccessoryIssue: ...

    @abstractmethod
    def list(self, *, student_id: UUID | None = None,
             kind: AccessoryKind | None = None) -> list[AccessoryIssue]:
        """Newest first."""

    @abstractmethod
    def total_sold(self, student_id: UUID) -> dict[AccessoryKind, Decimal]: ...


class FeeStructureRepository(ABC):
    @abstractmethod
    def amounts_for(self, class_id: UUID) -> dict[FeeHead, Decimal]: ...

    @abstractmethod
    def set_amount(self, class_id: UUID, head: FeeHead, amount: Decimal) -> None: ...


class FeePaymentRepository(ABC):
    """Payments are never edited, so there is no update. The repository gives each
    one its receipt number."""

    @abstractmethod
    def add(self, payment: FeePayment) -> FeePayment: ...

    @abstractmethod
    def list(self, *, student_id: UUID | None = None, from_date: date | None = None,
             to_date: date | None = None) -> list[FeePayment]:
        """Newest first."""

    @abstractmethod
    def total_paid(self, student_id: UUID) -> dict[FeeHead, Decimal]: ...

    @abstractmethod
    def collected_by_month(self, from_date: date, to_date: date
                           ) -> dict[date, dict[FeeHead, Decimal]]:
        """What was collected in each month (keyed by its first day), by fee head."""
