from datetime import date
from uuid import UUID

from apps.accounts.domain.capabilities import MANAGE_SCHOOL
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import NotFound
from apps.core.domain.usecase import UseCase

from ..entities import Holiday
from ..repositories import HolidayRepository


class ListHolidays(UseCase):
    def __init__(self, holidays: HolidayRepository):
        self._holidays = holidays

    def call(self, *, from_date: date | None = None,
             to_date: date | None = None) -> list[Holiday]:
        return self._holidays.list(from_date=from_date, to_date=to_date)


class _HolidayWriter(UseCase):
    def __init__(self, holidays: HolidayRepository, authorizer: Authorizer,
                 audit: AuditLogger):
        self._holidays = holidays
        self._authorizer = authorizer
        self._audit = audit

    def _existing(self, holiday_id: UUID) -> Holiday:
        holiday = self._holidays.get(holiday_id)
        if holiday is None or not holiday.is_active:
            raise NotFound("This holiday was not found.")
        return holiday


class AddHoliday(_HolidayWriter):
    def call(self, actor: UserAccount, *, name: str, starts_on: date,
             ends_on: date | None = None) -> Holiday:
        self._authorizer.require(actor, MANAGE_SCHOOL)
        saved = self._holidays.add(Holiday.declare(name=name, starts_on=starts_on, ends_on=ends_on))
        self._audit.record(actor.id, "holiday_added", f"holiday:{saved.id}", {"name": saved.name})
        return saved


class UpdateHoliday(_HolidayWriter):
    """Changes only what is given; the rest stays."""

    def call(self, actor: UserAccount, holiday_id: UUID, *, name: str | None = None,
             starts_on: date | None = None, ends_on: date | None = None) -> Holiday:
        self._authorizer.require(actor, MANAGE_SCHOOL)
        holiday = self._existing(holiday_id)
        holiday.change(
            name=holiday.name if name is None else name,
            starts_on=holiday.starts_on if starts_on is None else starts_on,
            ends_on=holiday.ends_on if ends_on is None else ends_on,
        )
        saved = self._holidays.update(holiday)
        self._audit.record(actor.id, "holiday_updated", f"holiday:{saved.id}", {"name": saved.name})
        return saved


class RemoveHoliday(_HolidayWriter):
    def call(self, actor: UserAccount, holiday_id: UUID) -> None:
        self._authorizer.require(actor, MANAGE_SCHOOL)
        holiday = self._existing(holiday_id)
        holiday.remove()
        self._holidays.update(holiday)
        self._audit.record(actor.id, "holiday_removed", f"holiday:{holiday.id}",
                           {"name": holiday.name})
