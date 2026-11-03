from dataclasses import dataclass

from apps.core.domain.usecase import UseCase

from ..entities import Season, SeasonSchedule
from ..repositories import ScheduleRepository, SchoolRepository


@dataclass(frozen=True)
class Timings:
    active_season: Season | None
    # Every season is listed; None means the Principal has not set that season yet.
    by_season: dict[Season, SeasonSchedule | None]


class GetTimings(UseCase):
    def __init__(self, schools: SchoolRepository, schedules: ScheduleRepository):
        self._schools = schools
        self._schedules = schedules

    def call(self) -> Timings:
        school = self._schools.current()
        return Timings(
            active_season=school.active_season,
            by_season={season: self._schedules.get(season) for season in Season},
        )
