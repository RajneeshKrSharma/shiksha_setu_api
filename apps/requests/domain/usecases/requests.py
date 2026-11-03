from datetime import date, time
from uuid import UUID

from apps.accounts.domain.capabilities import RAISE_MEETING_QUERY, RECORD_OWN_ATTENDANCE
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.audit import AuditLogger
from apps.core.domain.clock import Clock
from apps.core.domain.errors import NotFound, RuleViolation
from apps.core.domain.usecase import UseCase

from ..entities import LeaveRequest, MeetingRequest, Request, RequestKind, RequestStatus
from ..repositories import RequestRepository
from ..services import RequestVisibility


class RaiseLeave(UseCase):
    """Asks for leave. Days already covered by another pending or approved leave of the
    same person are not asked for twice."""

    def __init__(self, requests: RequestRepository, authorizer: Authorizer, clock: Clock):
        self._requests = requests
        self._authorizer = authorizer
        self._clock = clock

    def call(self, actor: UserAccount, *, starts_on: date, ends_on: date,
             reason: str) -> LeaveRequest:
        self._authorizer.require(actor, RECORD_OWN_ATTENDANCE)
        leave = LeaveRequest.apply(requester_id=actor.id, starts_on=starts_on, ends_on=ends_on,
                                   reason=reason, today=self._clock.today())
        if self._requests.has_leave_between(actor.id, leave.starts_on, leave.ends_on):
            message = "You already have a leave on some of these days."
            raise RuleViolation(message, errors={"starts_on": [message]})
        return self._requests.add(leave)


class RaiseMeetingQuery(UseCase):
    def __init__(self, requests: RequestRepository, authorizer: Authorizer, clock: Clock):
        self._requests = requests
        self._authorizer = authorizer
        self._clock = clock

    def call(self, actor: UserAccount, *, subject: str, details: str = "",
             preferred_on: date | None = None) -> MeetingRequest:
        self._authorizer.require(actor, RAISE_MEETING_QUERY)
        meeting = MeetingRequest.ask(requester_id=actor.id, subject=subject, details=details,
                                     preferred_on=preferred_on, today=self._clock.today())
        return self._requests.add(meeting)


class ListRequests(UseCase):
    """A person gets their own requests; whoever may decide a kind also gets everyone's of
    that kind."""

    def __init__(self, requests: RequestRepository, visibility: RequestVisibility):
        self._requests = requests
        self._visibility = visibility

    def call(self, actor: UserAccount, *, kind: RequestKind | None = None,
             status: RequestStatus | None = None,
             requester_id: UUID | None = None) -> list[Request]:
        found = self._requests.list(kind=kind, status=status, requester_id=requester_id)
        return [r for r in found if self._visibility.can_see(actor, r)]


class _Decision(UseCase):
    def __init__(self, requests: RequestRepository, authorizer: Authorizer, audit: AuditLogger,
                 clock: Clock):
        self._requests = requests
        self._authorizer = authorizer
        self._audit = audit
        self._clock = clock

    def _deciding(self, actor: UserAccount, request_id: UUID) -> Request:
        request = self._requests.get(request_id)
        if request is None:
            raise NotFound("This request was not found.")
        self._authorizer.require(actor, request.decision_right)
        return request

    def _record(self, actor: UserAccount, action: str, request: Request) -> None:
        self._audit.record(actor.id, action, f"user:{request.requester_id}", {
            "kind": request.kind.value, "note": request.decision_note,
        })


class ApproveRequest(_Decision):
    """Approves a request under the right that belongs to its kind. A meeting needs the
    day and time (`terms`); a leave needs nothing."""

    def call(self, actor: UserAccount, request_id: UUID, *, meeting_on: date | None = None,
             meeting_at: time | None = None) -> Request:
        request = self._deciding(actor, request_id)
        terms = {k: v for k, v in (("meeting_on", meeting_on), ("meeting_at", meeting_at))
                 if v is not None}
        request.approve(by_id=actor.id, on=self._clock.today(), **terms)
        saved = self._requests.update(request)
        self._record(actor, "request_approved", saved)
        return saved


class RejectRequest(_Decision):
    def call(self, actor: UserAccount, request_id: UUID, *, reason: str) -> Request:
        request = self._deciding(actor, request_id)
        request.reject(by_id=actor.id, on=self._clock.today(), reason=reason)
        saved = self._requests.update(request)
        self._record(actor, "request_rejected", saved)
        return saved


class WithdrawRequest(UseCase):
    """The person who asked takes the request back, while it is still waiting."""

    def __init__(self, requests: RequestRepository):
        self._requests = requests

    def call(self, actor: UserAccount, request_id: UUID) -> None:
        request = self._requests.get(request_id)
        if request is None or request.requester_id != actor.id:
            raise NotFound("This request was not found.")
        request.withdraw(by_id=actor.id)
        self._requests.update(request)
