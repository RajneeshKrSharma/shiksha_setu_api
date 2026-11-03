from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from ..domain.entities import (
    LeaveRequest,
    MeetingRequest,
    Request,
    RequestKind,
    RequestStatus,
)
from ..domain.repositories import RequestRepository
from . import models as rows

_COUNTED = [RequestStatus.PENDING.value, RequestStatus.APPROVED.value]


class KindMapper(ABC):
    """Moves one kind of request to and from its columns in the shared table."""

    kind: RequestKind

    @abstractmethod
    def columns(self, request: Request) -> dict: ...

    @abstractmethod
    def build(self, row: rows.Request, common: dict) -> Request: ...


class LeaveMapper(KindMapper):
    kind = RequestKind.LEAVE

    def columns(self, request: LeaveRequest) -> dict:
        return {"starts_on": request.starts_on, "ends_on": request.ends_on,
                "reason": request.reason}

    def build(self, row: rows.Request, common: dict) -> LeaveRequest:
        return LeaveRequest(starts_on=row.starts_on, ends_on=row.ends_on, reason=row.reason,
                            **common)


class MeetingMapper(KindMapper):
    kind = RequestKind.MEETING

    def columns(self, request: MeetingRequest) -> dict:
        return {"subject": request.subject, "details": request.details,
                "preferred_on": request.preferred_on, "meeting_on": request.meeting_on,
                "meeting_at": request.meeting_at}

    def build(self, row: rows.Request, common: dict) -> MeetingRequest:
        return MeetingRequest(subject=row.subject, details=row.details,
                              preferred_on=row.preferred_on, meeting_on=row.meeting_on,
                              meeting_at=row.meeting_at, **common)


class DjangoRequestRepository(RequestRepository):
    """Every kind lives in one table. A new kind adds a mapper here, nothing else."""

    def __init__(self, mappers: list[KindMapper] | None = None):
        mappers = mappers or [LeaveMapper(), MeetingMapper()]
        self._mappers = {mapper.kind: mapper for mapper in mappers}

    def get(self, entity_id: UUID) -> Request | None:
        row = self._rows().filter(pk=entity_id).first()
        return self._entity(row) if row else None

    def add(self, request: Request) -> Request:
        row = rows.Request.objects.create(
            kind=request.kind.value, requester_id=request.requester_id,
            **self._mappers[request.kind].columns(request),
        )
        return self.get(row.pk)

    def update(self, request: Request) -> Request:
        row = rows.Request.objects.get(pk=request.id)
        row.status, row.decided_by_id = request.status.value, request.decided_by_id
        row.decided_on, row.decision_note = request.decided_on, request.decision_note
        for column, value in self._mappers[request.kind].columns(request).items():
            setattr(row, column, value)
        row.save()
        return self.get(row.pk)

    def list(self, *, kind: RequestKind | None = None, status: RequestStatus | None = None,
             requester_id: UUID | None = None) -> list[Request]:
        found = self._rows()
        if kind is not None:
            found = found.filter(kind=kind.value)
        if status is not None:
            found = found.filter(status=status.value)
        if requester_id is not None:
            found = found.filter(requester_id=requester_id)
        return [self._entity(row) for row in found]

    def has_leave_between(self, requester_id: UUID, starts_on: date, ends_on: date) -> bool:
        return rows.Request.objects.filter(
            kind=RequestKind.LEAVE.value, requester_id=requester_id, status__in=_COUNTED,
            starts_on__lte=ends_on, ends_on__gte=starts_on,
        ).exists()

    def people_on_leave(self, day: date) -> frozenset[UUID]:
        return frozenset(
            rows.Request.objects.filter(
                kind=RequestKind.LEAVE.value, status=RequestStatus.APPROVED.value,
                starts_on__lte=day, ends_on__gte=day,
            ).values_list("requester_id", flat=True)
        )

    @staticmethod
    def _rows():
        return rows.Request.objects.select_related("requester", "decided_by")

    def _entity(self, row: rows.Request) -> Request:
        common = dict(
            id=row.pk, requester_id=row.requester_id, status=RequestStatus(row.status),
            decided_by_id=row.decided_by_id, decided_on=row.decided_on,
            decision_note=row.decision_note, created_on=row.created_at.date(),
            requester_name=row.requester.name, requester_role=row.requester.role,
            decided_by_name=row.decided_by.name if row.decided_by else "",
        )
        return self._mappers[RequestKind(row.kind)].build(row, common)
