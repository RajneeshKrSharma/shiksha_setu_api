from datetime import date
from uuid import UUID

from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.attendance.domain.ports import LeaveCalendar

from .entities import Request
from .repositories import RequestRepository


class ApprovedLeaves(LeaveCalendar):
    """Tells attendance who is on approved leave on a day."""

    def __init__(self, requests: RequestRepository):
        self._requests = requests

    def people_on_leave(self, day: date) -> frozenset[UUID]:
        return self._requests.people_on_leave(day)


class RequestVisibility:
    """Who sees which requests: a person sees their own; whoever may decide a kind sees
    every request of that kind."""

    def __init__(self, authorizer: Authorizer):
        self._authorizer = authorizer

    def can_see(self, actor: UserAccount, request: Request) -> bool:
        return request.requester_id == actor.id or self._authorizer.can(
            actor, request.decision_right
        )
