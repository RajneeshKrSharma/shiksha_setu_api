from apps.accounts.domain.capabilities import MANAGE_SCHOOL
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.errors import RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import School, Season
from ..repositories import SchoolRepository


class UpdateSchool(UseCase):
    """Sets the school's name and/or which season's timing is in use."""

    def __init__(self, schools: SchoolRepository, authorizer: Authorizer, audit: AuditLogger):
        self._schools = schools
        self._authorizer = authorizer
        self._audit = audit

    def call(self, actor: UserAccount, *, name: str | None = None,
             active_season: Season | None = None) -> School:
        self._authorizer.require(actor, MANAGE_SCHOOL)
        if name is None and active_season is None:
            raise RuleViolation("Nothing to change.")
        school = self._schools.current()
        if name is not None:
            school.rename(name)
        if active_season is not None:
            school.switch_season(active_season)
        saved = self._schools.save(school)
        self._audit.record(actor.id, "school_updated", "school", {
            "name": saved.name,
            "active_season": saved.active_season.value if saved.active_season else None,
        })
        return saved
