from __future__ import annotations

from datetime import date
from uuid import UUID

from django.db.models import Max, Min, Q

from apps.accounts.domain.entities import Role, UserAccount
from apps.accounts.domain.repositories import UserRepository

from ..domain.entities import StaffMember, Van
from ..domain.fuel import BillStatus, FuelBill, FuelType
from ..domain.repositories import FuelBillRepository, StaffRepository, VanRepository
from . import models as rows

_COUNTED = [BillStatus.PENDING.value, BillStatus.APPROVED.value]


class DjangoStaffRepository(StaffRepository):
    """A staff member is a sign-in account with the staff role plus a job title, so this
    works through the accounts module's repository."""

    def __init__(self, users: UserRepository):
        self._users = users

    def get(self, entity_id: UUID) -> StaffMember | None:
        account = self._users.get(entity_id)
        if account is None or account.role != Role.STAFF:
            return None
        return StaffMember.from_account(account, self._title(entity_id))

    def add(self, staff: StaffMember, password: str | None = None) -> StaffMember:
        account = UserAccount.register(name=staff.name, email=staff.email, role=Role.STAFF)
        saved = self._users.add(account, password)
        self.set_job_title(saved.id, staff.job_title)
        return StaffMember.from_account(saved, staff.job_title)

    def update(self, staff: StaffMember) -> StaffMember:
        account = self._users.get(staff.id)
        account.name, account.is_active = staff.name, staff.is_active
        saved = self._users.update(account)
        self.set_job_title(staff.id, staff.job_title)
        return StaffMember.from_account(saved, staff.job_title)

    def set_job_title(self, staff_id: UUID, job_title: str) -> None:
        rows.StaffProfile.objects.update_or_create(
            user_id=staff_id, defaults={"job_title": job_title}
        )

    def list(self, *, query: str = "", active: bool | None = None) -> list[StaffMember]:
        accounts = self._users.list(role=Role.STAFF, query=query, active=active)
        titles = dict(
            rows.StaffProfile.objects.filter(user_id__in=[a.id for a in accounts])
            .values_list("user_id", "job_title")
        )
        return [StaffMember.from_account(a, titles.get(a.id, "")) for a in accounts]

    @staticmethod
    def _title(staff_id: UUID) -> str:
        profile = rows.StaffProfile.objects.filter(user_id=staff_id).first()
        return profile.job_title if profile else ""


class DjangoVanRepository(VanRepository):
    def get(self, entity_id: UUID) -> Van | None:
        row = self._rows().filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, van: Van) -> Van:
        row = rows.Van.objects.create(name=van.name, driver_id=van.driver_id)
        return self.get(row.pk)

    def update(self, van: Van) -> Van:
        row = rows.Van.objects.get(pk=van.id)
        row.name, row.driver_id, row.is_active = van.name, van.driver_id, van.is_active
        row.save(update_fields=["name", "driver", "is_active", "updated_at"])
        return self.get(row.pk)

    def list(self, *, active: bool = True, driver_id: UUID | None = None) -> list[Van]:
        found = self._rows().filter(is_active=active)
        if driver_id is not None:
            found = found.filter(driver_id=driver_id)
        return [self._entity(row) for row in found]

    def find_active_by_name(self, name: str) -> Van | None:
        row = self._rows().filter(name__iexact=name, is_active=True).first()
        return self._entity(row) if row else None

    def find_driven_by(self, driver_id: UUID) -> Van | None:
        row = self._rows().filter(driver_id=driver_id, is_active=True).first()
        return self._entity(row) if row else None

    @staticmethod
    def _rows():
        return rows.Van.objects.select_related("driver")

    @staticmethod
    def _entity(row: rows.Van) -> Van:
        return Van(
            id=row.pk, name=row.name, driver_id=row.driver_id, is_active=row.is_active,
            driver_name=row.driver.name if row.driver else "",
        )


class DjangoFuelBillRepository(FuelBillRepository):
    def get(self, entity_id: UUID) -> FuelBill | None:
        row = self._rows().filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, bill: FuelBill) -> FuelBill:
        row = rows.FuelBill.objects.create(
            van_id=bill.van_id, submitted_by_id=bill.submitted_by_id, payee_id=bill.payee_id,
            billed_on=bill.billed_on,
            fuel=bill.fuel.value, litres=bill.litres, rate=bill.rate,
            odometer_km=bill.odometer_km,
        )
        return self.get(row.pk)

    def update(self, bill: FuelBill) -> FuelBill:
        row = rows.FuelBill.objects.get(pk=bill.id)
        row.status, row.decided_by_id = bill.status.value, bill.decided_by_id
        row.decided_on, row.reject_reason = bill.decided_on, bill.reject_reason
        row.save(update_fields=[
            "status", "decided_by", "decided_on", "reject_reason", "updated_at",
        ])
        return self.get(row.pk)

    def list(self, *, van_id: UUID | None = None, submitted_by_id: UUID | None = None,
             status: BillStatus | None = None, from_date: date | None = None,
             to_date: date | None = None, payee_id: UUID | None = None) -> list[FuelBill]:
        found = self._rows()
        if payee_id is not None:
            found = found.filter(payee_id=payee_id)
        if van_id is not None:
            found = found.filter(van_id=van_id)
        if submitted_by_id is not None:
            found = found.filter(submitted_by_id=submitted_by_id)
        if status is not None:
            found = found.filter(status=status.value)
        if from_date is not None:
            found = found.filter(billed_on__gte=from_date)
        if to_date is not None:
            found = found.filter(billed_on__lte=to_date)
        return [self._entity(row) for row in found]

    def highest_odometer_up_to(self, van_id: UUID, day: date) -> int | None:
        return rows.FuelBill.objects.filter(
            van_id=van_id, status__in=_COUNTED, billed_on__lte=day
        ).aggregate(top=Max("odometer_km"))["top"]

    def lowest_odometer_after(self, van_id: UUID, day: date) -> int | None:
        return rows.FuelBill.objects.filter(
            van_id=van_id, status__in=_COUNTED, billed_on__gt=day
        ).aggregate(low=Min("odometer_km"))["low"]

    def previous_by_odometer(self, van_id: UUID, odometer_km: int,
                             exclude_id: UUID | None = None) -> FuelBill | None:
        found = self._rows().filter(
            van_id=van_id, status__in=_COUNTED, odometer_km__lt=odometer_km
        )
        if exclude_id is not None:
            found = found.exclude(pk=exclude_id)
        row = found.order_by("-odometer_km").first()
        return self._entity(row) if row else None

    @staticmethod
    def _rows():
        return rows.FuelBill.objects.select_related("van", "submitted_by", "decided_by")

    @staticmethod
    def _entity(row: rows.FuelBill) -> FuelBill:
        return FuelBill(
            id=row.pk, van_id=row.van_id, submitted_by_id=row.submitted_by_id,
            payee_id=row.payee_id, billed_on=row.billed_on, fuel=FuelType(row.fuel), litres=row.litres, rate=row.rate,
            odometer_km=row.odometer_km, status=BillStatus(row.status),
            decided_by_id=row.decided_by_id, decided_on=row.decided_on,
            reject_reason=row.reject_reason, van_name=row.van.name,
            submitted_by_name=row.submitted_by.name,
            decided_by_name=row.decided_by.name if row.decided_by else "",
        )
