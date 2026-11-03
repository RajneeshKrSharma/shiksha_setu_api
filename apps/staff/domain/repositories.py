from abc import abstractmethod
from datetime import date
from uuid import UUID

from apps.core.domain.repository import MemberRepository, Repository

from .entities import StaffMember, Van
from .fuel import BillStatus, FuelBill


class StaffRepository(MemberRepository[StaffMember]):
    """Staff are sign-in accounts with the staff role, plus a job title."""

    @abstractmethod
    def add(self, staff: StaffMember, password: str | None = None) -> StaffMember: ...

    @abstractmethod
    def set_job_title(self, staff_id: UUID, job_title: str) -> None: ...


class VanRepository(Repository[Van]):
    @abstractmethod
    def list(self, *, active: bool = True, driver_id: UUID | None = None) -> list[Van]:
        """By name."""

    @abstractmethod
    def find_active_by_name(self, name: str) -> Van | None:
        """Ignoring letter case."""

    @abstractmethod
    def find_driven_by(self, driver_id: UUID) -> Van | None:
        """The active van this person drives."""


class FuelBillRepository(Repository[FuelBill]):
    @abstractmethod
    def list(self, *, van_id: UUID | None = None, submitted_by_id: UUID | None = None,
             status: BillStatus | None = None, from_date: date | None = None,
             to_date: date | None = None, payee_id: UUID | None = None) -> list[FuelBill]:
        """Newest first."""

    @abstractmethod
    def highest_odometer_up_to(self, van_id: UUID, day: date) -> int | None:
        """Among counted bills dated on or before `day`."""

    @abstractmethod
    def lowest_odometer_after(self, van_id: UUID, day: date) -> int | None:
        """Among counted bills dated after `day`."""

    @abstractmethod
    def previous_by_odometer(self, van_id: UUID, odometer_km: int,
                             exclude_id: UUID | None = None) -> FuelBill | None:
        """The counted bill with the highest odometer below `odometer_km`."""
