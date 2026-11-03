from django.conf import settings
from django.db import models

from apps.core.data.base_model import BaseModel

from ..domain.entities import RequestKind, RequestStatus


class Request(BaseModel):
    """One table for every kind of request; a kind uses only its own columns."""

    kind = models.CharField(max_length=10, choices=[(k.value, k.value.title()) for k in RequestKind])
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requests_made"
    )
    status = models.CharField(
        max_length=10, choices=[(s.value, s.value.title()) for s in RequestStatus],
        default=RequestStatus.PENDING.value, db_index=True,
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    decided_on = models.DateField(null=True, blank=True)
    decision_note = models.CharField(max_length=300, blank=True)

    # leave
    starts_on = models.DateField(null=True, blank=True, db_index=True)
    ends_on = models.DateField(null=True, blank=True)
    reason = models.CharField(max_length=300, blank=True)

    # meeting
    subject = models.CharField(max_length=120, blank=True)
    details = models.CharField(max_length=1000, blank=True)
    preferred_on = models.DateField(null=True, blank=True)
    meeting_on = models.DateField(null=True, blank=True)
    meeting_at = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
