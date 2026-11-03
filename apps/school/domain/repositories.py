from abc import ABC, abstractmethod
from datetime import date

from apps.core.domain.repository import Repository

from .entities import Holiday, Notice, NoticeKind, School, Season, SeasonSchedule


class SchoolRepository(ABC):
    @abstractmethod
    def current(self) -> School:
        """The school; made empty the first time it is asked for."""

    @abstractmethod
    def save(self, school: School) -> School: ...


class ScheduleRepository(ABC):
    @abstractmethod
    def get(self, season: Season) -> SeasonSchedule | None: ...

    @abstractmethod
    def save(self, schedule: SeasonSchedule) -> SeasonSchedule:
        """Replaces the season's whole day (hours and periods) in one step."""


class HolidayRepository(Repository[Holiday]):
    @abstractmethod
    def list(self, *, from_date: date | None = None,
             to_date: date | None = None) -> list[Holiday]:
        """Active holidays that touch the given dates, earliest first."""


class NoticeRepository(Repository[Notice]):
    @abstractmethod
    def list(self, *, kind: NoticeKind | None = None, limit: int = 50) -> list[Notice]:
        """Active notices, newest first."""
