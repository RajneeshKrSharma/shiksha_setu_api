from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import StrEnum
from uuid import UUID

from apps.core.domain.entity import Entity
from apps.core.domain.errors import RuleViolation


def _invalid(field_name: str, message: str) -> RuleViolation:
    return RuleViolation(message, errors={field_name: [message]})


class Season(StrEnum):
    SUMMER = "summer"
    WINTER = "winter"

    @property
    def label(self) -> str:
        return self.value.title()


class NoticeKind(StrEnum):
    NOTICE = "notice"
    ANNOUNCEMENT = "announcement"


@dataclass(eq=False, kw_only=True)
class School(Entity):
    """The one school this app runs. The Principal chooses which season's timing is in use."""

    NAME_MAX = 120

    name: str = ""
    active_season: Season | None = None

    def rename(self, name: str) -> None:
        name = name.strip()
        if not name or len(name) > self.NAME_MAX:
            raise _invalid("school_name", f"Required, up to {self.NAME_MAX} characters.")
        self.name = name

    def switch_season(self, season: Season) -> None:
        self.active_season = season


@dataclass(frozen=True)
class Period:
    number: int
    name: str
    starts_at: time
    ends_at: time


@dataclass(eq=False, kw_only=True)
class SeasonSchedule(Entity):
    """One season's school day: when it opens and closes, and its periods in order.
    The rules for a valid day are kept here, so no caller can build a broken one."""

    NAME_MAX = 60

    season: Season
    opens_at: time
    closes_at: time
    periods: list[Period] = field(default_factory=list)

    @classmethod
    def plan(cls, *, season: Season, opens_at: time, closes_at: time,
             periods: list[tuple[str, time, time]]) -> "SeasonSchedule":
        """[periods] are (name, starts_at, ends_at); they are numbered 1, 2, ... by start time."""
        if closes_at <= opens_at:
            raise _invalid("closes_at", "The school must close after it opens.")
        built: list[Period] = []
        for name, starts_at, ends_at in sorted(periods, key=lambda p: p[1]):
            number = len(built) + 1
            name = name.strip()
            if len(name) > cls.NAME_MAX:
                raise _invalid("periods", f"Period {number}: name is up to {cls.NAME_MAX} characters.")
            if ends_at <= starts_at:
                raise _invalid("periods", f"Period {number} must end after it starts.")
            if starts_at < opens_at or ends_at > closes_at:
                raise _invalid("periods", f"Period {number} must be within the school hours.")
            if built and starts_at < built[-1].ends_at:
                raise _invalid("periods", f"Period {number} overlaps period {number - 1}.")
            built.append(Period(number, name, starts_at, ends_at))
        return cls(season=season, opens_at=opens_at, closes_at=closes_at, periods=built)


@dataclass(eq=False, kw_only=True)
class Holiday(Entity):
    NAME_MAX = 120

    name: str
    starts_on: date
    ends_on: date
    is_active: bool = True

    @classmethod
    def declare(cls, *, name: str, starts_on: date, ends_on: date | None = None) -> "Holiday":
        holiday = cls(name="-", starts_on=starts_on, ends_on=ends_on or starts_on)
        holiday.change(name=name, starts_on=starts_on, ends_on=ends_on or starts_on)
        return holiday

    def change(self, *, name: str, starts_on: date, ends_on: date) -> None:
        name = name.strip()
        if not name or len(name) > self.NAME_MAX:
            raise _invalid("name", f"Required, up to {self.NAME_MAX} characters.")
        if ends_on < starts_on:
            raise _invalid("ends_on", "The last day cannot be before the first day.")
        self.name, self.starts_on, self.ends_on = name, starts_on, ends_on

    def remove(self) -> None:
        self.is_active = False


@dataclass(eq=False, kw_only=True)
class Notice(Entity):
    TITLE_MAX = 150
    BODY_MAX = 2000

    kind: NoticeKind
    title: str
    body: str
    posted_by_id: UUID | None = None
    # Filled in when read, so the app can show who posted it.
    posted_by_name: str = ""
    posted_at: datetime | None = None
    is_active: bool = True

    @classmethod
    def post(cls, *, kind: NoticeKind, title: str, body: str, posted_by_id: UUID) -> "Notice":
        title, body = title.strip(), body.strip()
        if not title or len(title) > cls.TITLE_MAX:
            raise _invalid("title", f"Required, up to {cls.TITLE_MAX} characters.")
        if not body or len(body) > cls.BODY_MAX:
            raise _invalid("body", f"Required, up to {cls.BODY_MAX} characters.")
        return cls(kind=kind, title=title, body=body, posted_by_id=posted_by_id)

    def withdraw(self) -> None:
        self.is_active = False
