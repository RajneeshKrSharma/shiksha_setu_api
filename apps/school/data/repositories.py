from datetime import date
from uuid import UUID

from django.db import transaction

from ..domain.entities import (
    Holiday,
    Notice,
    NoticeKind,
    Period,
    School,
    Season,
    SeasonSchedule,
)
from ..domain.repositories import (
    HolidayRepository,
    NoticeRepository,
    ScheduleRepository,
    SchoolRepository,
)
from . import models as rows


class DjangoSchoolRepository(SchoolRepository):
    def current(self) -> School:
        row = rows.School.objects.first() or rows.School.objects.create()
        return self._entity(row)

    def save(self, school: School) -> School:
        row = rows.School.objects.get(pk=school.id)
        row.name = school.name
        row.active_season = school.active_season.value if school.active_season else ""
        row.save(update_fields=["name", "active_season", "updated_at"])
        return self._entity(row)

    def _entity(self, row: rows.School) -> School:
        return School(
            id=row.pk,
            name=row.name,
            active_season=Season(row.active_season) if row.active_season else None,
        )


class DjangoScheduleRepository(ScheduleRepository):
    def get(self, season: Season) -> SeasonSchedule | None:
        row = rows.SeasonTiming.objects.filter(season=season.value).first()
        return self._entity(row) if row else None

    @transaction.atomic
    def save(self, schedule: SeasonSchedule) -> SeasonSchedule:
        timing, _ = rows.SeasonTiming.objects.update_or_create(
            season=schedule.season.value,
            defaults={"opens_at": schedule.opens_at, "closes_at": schedule.closes_at},
        )
        timing.periods.all().delete()
        rows.SchoolPeriod.objects.bulk_create([
            rows.SchoolPeriod(
                timing=timing, number=p.number, name=p.name,
                starts_at=p.starts_at, ends_at=p.ends_at,
            )
            for p in schedule.periods
        ])
        return self._entity(timing)

    def _entity(self, row: rows.SeasonTiming) -> SeasonSchedule:
        return SeasonSchedule(
            id=row.pk,
            season=Season(row.season),
            opens_at=row.opens_at,
            closes_at=row.closes_at,
            periods=[
                Period(p.number, p.name, p.starts_at, p.ends_at) for p in row.periods.all()
            ],
        )


class DjangoHolidayRepository(HolidayRepository):
    def get(self, entity_id: UUID) -> Holiday | None:
        row = rows.Holiday.objects.filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, holiday: Holiday) -> Holiday:
        row = rows.Holiday.objects.create(
            name=holiday.name, starts_on=holiday.starts_on, ends_on=holiday.ends_on
        )
        return self._entity(row)

    def update(self, holiday: Holiday) -> Holiday:
        row = rows.Holiday.objects.get(pk=holiday.id)
        row.name, row.starts_on, row.ends_on = holiday.name, holiday.starts_on, holiday.ends_on
        row.is_active = holiday.is_active
        row.save(update_fields=["name", "starts_on", "ends_on", "is_active", "updated_at"])
        return self._entity(row)

    def list(self, *, from_date: date | None = None,
             to_date: date | None = None) -> list[Holiday]:
        found = rows.Holiday.objects.filter(is_active=True)
        if from_date is not None:
            found = found.filter(ends_on__gte=from_date)
        if to_date is not None:
            found = found.filter(starts_on__lte=to_date)
        return [self._entity(row) for row in found]

    def _entity(self, row: rows.Holiday) -> Holiday:
        return Holiday(
            id=row.pk, name=row.name, starts_on=row.starts_on, ends_on=row.ends_on,
            is_active=row.is_active,
        )


class DjangoNoticeRepository(NoticeRepository):
    def get(self, entity_id: UUID) -> Notice | None:
        row = rows.Notice.objects.select_related("posted_by").filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, notice: Notice) -> Notice:
        row = rows.Notice.objects.create(
            kind=notice.kind.value, title=notice.title, body=notice.body,
            posted_by_id=notice.posted_by_id,
        )
        return self.get(row.pk)

    def update(self, notice: Notice) -> Notice:
        row = rows.Notice.objects.get(pk=notice.id)
        row.is_active = notice.is_active
        row.save(update_fields=["is_active", "updated_at"])
        return self.get(row.pk)

    def list(self, *, kind: NoticeKind | None = None, limit: int = 50) -> list[Notice]:
        found = rows.Notice.objects.select_related("posted_by").filter(is_active=True)
        if kind is not None:
            found = found.filter(kind=kind.value)
        return [self._entity(row) for row in found[:limit]]

    def _entity(self, row: rows.Notice) -> Notice:
        return Notice(
            id=row.pk,
            kind=NoticeKind(row.kind),
            title=row.title,
            body=row.body,
            posted_by_id=row.posted_by_id,
            posted_by_name=row.posted_by.name if row.posted_by else "",
            posted_at=row.created_at,
            is_active=row.is_active,
        )
