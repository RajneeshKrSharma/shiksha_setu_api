from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum
from typing import ClassVar
from uuid import UUID

from apps.accounts.domain.capabilities import APPROVE_LEAVES, DECIDE_REQUESTS, Capability
from apps.core.domain.entity import Entity
from apps.core.domain.errors import RuleViolation


def _invalid(field: str, message: str) -> RuleViolation:
    return RuleViolation(message, errors={field: [message]})


class RequestKind(StrEnum):
    LEAVE = "leave"
    MEETING = "meeting"


class RequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


@dataclass(eq=False, kw_only=True)
class Request(Entity, ABC):
    """Something a person asks the Principal for. Each kind says which right decides it
    and what an approval needs; asking, deciding and withdrawing work the same for all."""

    REASON_MAX = 300

    kind: ClassVar[RequestKind]
    # The right needed to approve or reject this kind.
    decision_right: ClassVar[Capability]

    requester_id: UUID
    status: RequestStatus = RequestStatus.PENDING
    decided_by_id: UUID | None = None
    decided_on: date | None = None
    decision_note: str = ""
    created_on: date | None = None
    # Filled in when read, so the app can show them.
    requester_name: str = ""
    requester_role: str = ""
    decided_by_name: str = ""

    def approve(self, *, by_id: UUID, on: date, **terms) -> None:
        self._require_open(by_id)
        self._accept(on=on, **terms)
        self._decide(RequestStatus.APPROVED, by_id, on, "")

    def reject(self, *, by_id: UUID, on: date, reason: str) -> None:
        self._require_open(by_id)
        reason = reason.strip()
        if not reason or len(reason) > self.REASON_MAX:
            raise _invalid("reason", f"A reason is required, up to {self.REASON_MAX} characters.")
        self._decide(RequestStatus.REJECTED, by_id, on, reason)

    def withdraw(self, *, by_id: UUID) -> None:
        if by_id != self.requester_id:
            raise RuleViolation("Only the person who asked can withdraw this request.")
        self._require_pending()
        self.status = RequestStatus.WITHDRAWN

    @abstractmethod
    def _accept(self, *, on: date, **terms) -> None:
        """What this kind needs when it is approved; raises if it is not there."""

    def _decide(self, status: RequestStatus, by_id: UUID, on: date, note: str) -> None:
        self.status, self.decided_by_id, self.decided_on = status, by_id, on
        self.decision_note = note

    def _require_open(self, by_id: UUID) -> None:
        self._require_pending()
        if by_id == self.requester_id:
            raise RuleViolation("You cannot decide your own request.")

    def _require_pending(self) -> None:
        if self.status != RequestStatus.PENDING:
            raise RuleViolation(f"This request is already {self.status.value}.")


@dataclass(eq=False, kw_only=True)
class LeaveRequest(Request):
    """Leave from one day to another, both included."""

    kind = RequestKind.LEAVE
    decision_right = APPROVE_LEAVES

    starts_on: date
    ends_on: date
    reason: str

    @classmethod
    def apply(cls, *, requester_id: UUID, starts_on: date, ends_on: date, reason: str,
              today: date) -> "LeaveRequest":
        reason = reason.strip()
        if not reason or len(reason) > cls.REASON_MAX:
            raise _invalid("reason", f"Required, up to {cls.REASON_MAX} characters.")
        if starts_on < today:
            raise _invalid("starts_on", "Leave can start today or later, not on a past day.")
        if ends_on < starts_on:
            raise _invalid("ends_on", "The last day cannot be before the first day.")
        return cls(requester_id=requester_id, starts_on=starts_on, ends_on=ends_on, reason=reason)

    def covers(self, day: date) -> bool:
        return self.starts_on <= day <= self.ends_on

    def _accept(self, *, on: date, **terms) -> None:
        if terms:
            raise RuleViolation("A leave needs nothing more to be approved.")


@dataclass(eq=False, kw_only=True)
class MeetingRequest(Request):
    """A wish to meet the Principal. Approving it fixes the day and time."""

    SUBJECT_MAX = 120
    DETAILS_MAX = 1000

    kind = RequestKind.MEETING
    decision_right = DECIDE_REQUESTS

    subject: str
    details: str = ""
    preferred_on: date | None = None
    meeting_on: date | None = None
    meeting_at: time | None = None

    @classmethod
    def ask(cls, *, requester_id: UUID, subject: str, details: str, preferred_on: date | None,
            today: date) -> "MeetingRequest":
        subject, details = subject.strip(), details.strip()
        if not subject or len(subject) > cls.SUBJECT_MAX:
            raise _invalid("subject", f"Required, up to {cls.SUBJECT_MAX} characters.")
        if len(details) > cls.DETAILS_MAX:
            raise _invalid("details", f"Up to {cls.DETAILS_MAX} characters.")
        if preferred_on is not None and preferred_on < today:
            raise _invalid("preferred_on", "Choose today or a later day.")
        return cls(requester_id=requester_id, subject=subject, details=details,
                   preferred_on=preferred_on)

    def _accept(self, *, on: date, meeting_on: date | None = None, meeting_at: time | None = None,
                **terms) -> None:
        if terms:
            raise RuleViolation("Only the meeting day and time can be given.")
        if meeting_on is None or meeting_at is None:
            raise _invalid("meeting_on", "Give the day and time of the meeting.")
        if meeting_on < on:
            raise _invalid("meeting_on", "The meeting cannot be on a past day.")
        self.meeting_on, self.meeting_at = meeting_on, meeting_at
