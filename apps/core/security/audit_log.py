import uuid
from uuid import UUID

from django.db import models

from apps.core.domain.audit import AuditLogger


class AuditEntry(models.Model):
    """Written once, never edited."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_id = models.UUIDField(null=True, blank=True, db_index=True)
    action = models.CharField(max_length=60)
    target = models.CharField(max_length=120)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-at"]


class DatabaseAuditLogger(AuditLogger):
    def record(self, actor_id: UUID | None, action: str, target: str,
               details: dict | None = None) -> None:
        AuditEntry.objects.create(
            actor_id=actor_id, action=action, target=target, details=details or {}
        )
