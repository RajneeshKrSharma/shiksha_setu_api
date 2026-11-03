from rest_framework import serializers

from ..domain.entities import Request

_HHMM = {"format": "%H:%M", "input_formats": ["%H:%M", "%H:%M:%S"]}

# Each kind fills the fields that belong to it; the others are null.
_KIND_FIELDS = ("starts_on", "ends_on", "reason", "subject", "details", "preferred_on",
                "meeting_on", "meeting_at")


class LeaveInput(serializers.Serializer):
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    reason = serializers.CharField(max_length=300)


class MeetingInput(serializers.Serializer):
    subject = serializers.CharField(max_length=120)
    details = serializers.CharField(required=False, allow_blank=True, default="", max_length=1000)
    preferred_on = serializers.DateField(required=False, allow_null=True, default=None)


class ApproveInput(serializers.Serializer):
    meeting_on = serializers.DateField(required=False)
    meeting_at = serializers.TimeField(required=False, **_HHMM)


class RejectInput(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True)


class RequestOut(serializers.Serializer):
    def to_representation(self, request: Request):
        data = {
            "id": str(request.id),
            "kind": request.kind.value,
            "status": request.status.value,
            "requester_id": str(request.requester_id),
            "requester_name": request.requester_name,
            "requester_role": request.requester_role,
            "created_on": request.created_on.isoformat() if request.created_on else None,
            "decided_by_name": request.decided_by_name,
            "decided_on": request.decided_on.isoformat() if request.decided_on else None,
            "decision_note": request.decision_note,
        }
        for field in _KIND_FIELDS:
            value = getattr(request, field, None)
            data[field] = value.strftime("%H:%M") if field == "meeting_at" and value else (
                value.isoformat() if hasattr(value, "isoformat") else value
            )
        return data
