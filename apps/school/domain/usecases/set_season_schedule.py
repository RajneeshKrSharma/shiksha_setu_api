from datetime import time

from apps.accounts.domain.capabilities import MANAGE_SCHOOL
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.usecase import UseCase

from ..entities import Season, SeasonSchedule
from ..repositories import ScheduleRepository


class SetSeasonSchedule(UseCase):
    """Sets one season's school day. The whole day is replaced, so the Principal
    always sends the full list of periods."""

    def __init__(self, schedules: ScheduleRepository, authorizer: Authorizer,
                 audit: AuditLogger):
        self._schedules = schedules
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, *, season: Season, opens_at: time, closes_at: time,
             periods: list[tuple[str, time, time]]) -> SeasonSchedule:
        self._authorizer.require(actor, MANAGE_SCHOOL)
        schedule = SeasonSchedule.plan(
            season=season, opens_at=opens_at, closes_at=closes_at, periods=periods
        )
        saved = self._schedules.save(schedule)
        self._audit.record(actor.id, "timing_set", f"season:{season.value}",
                           {"periods": len(saved.periods)})
        return saved
