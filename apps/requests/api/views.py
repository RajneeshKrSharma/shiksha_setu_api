from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import CapabilityGate
from apps.accounts.domain.capabilities import (
    APPROVE_LEAVES,
    DECIDE_REQUESTS,
    RAISE_MEETING_QUERY,
    RECORD_OWN_ATTENDANCE,
)
from apps.core.api.query import QueryParams
from config.container import container

from ..domain.entities import RequestKind, RequestStatus
from .serializers import ApproveInput, LeaveInput, MeetingInput, RejectInput, RequestOut

_ASKERS = (RECORD_OWN_ATTENDANCE, RAISE_MEETING_QUERY)
_DECIDERS = (APPROVE_LEAVES, DECIDE_REQUESTS)


class RequestListView(APIView):
    permission_classes = [CapabilityGate.of(read=(*_ASKERS, *_DECIDERS), write=())]

    def get(self, request):
        query = QueryParams(request)
        found = container.list_requests().call(
            container.actor(request.user), kind=query.choice("kind", RequestKind),
            status=query.choice("status", RequestStatus), requester_id=query.uuid("requester_id"),
        )
        return Response(RequestOut(found, many=True).data)


class LeaveCreateView(APIView):
    permission_classes = [CapabilityGate.of(read=(), write=(RECORD_OWN_ATTENDANCE,))]

    def post(self, request):
        data = LeaveInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.raise_leave().call(container.actor(request.user), **data.validated_data)
        return Response(RequestOut(saved).data, status=201)


class MeetingCreateView(APIView):
    permission_classes = [CapabilityGate.of(read=(), write=(RAISE_MEETING_QUERY,))]

    def post(self, request):
        data = MeetingInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.raise_meeting_query().call(
            container.actor(request.user), **data.validated_data
        )
        return Response(RequestOut(saved).data, status=201)


class RequestDetailView(APIView):
    """Withdraws a request; only the person who asked can, and only while it waits."""

    permission_classes = [CapabilityGate.of(read=(), write=_ASKERS)]

    def delete(self, request, request_id):
        container.withdraw_request().call(container.actor(request.user), request_id)
        return Response(status=204)


class _DecisionView(APIView):
    permission_classes = [CapabilityGate.of(read=(), write=_DECIDERS)]


class RequestApproveView(_DecisionView):
    def post(self, request, request_id):
        data = ApproveInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.approve_request().call(
            container.actor(request.user), request_id, **data.validated_data
        )
        return Response(RequestOut(saved).data)


class RequestRejectView(_DecisionView):
    def post(self, request, request_id):
        data = RejectInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.reject_request().call(
            container.actor(request.user), request_id, reason=data.validated_data["reason"]
        )
        return Response(RequestOut(saved).data)
