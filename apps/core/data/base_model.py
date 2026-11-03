import uuid

from django.db import models


class BaseModel(models.Model):
    """UUID ids, timestamps and soft delete for every table. `updated_at` is what
    the app's sync will ask for ("everything changed since ...")."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
