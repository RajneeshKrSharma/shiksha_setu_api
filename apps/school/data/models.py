from django.conf import settings
from django.db import models

from apps.core.data.base_model import BaseModel

from ..domain.entities import NoticeKind, Season

SEASON_CHOICES = [(s.value, s.label) for s in Season]


class School(BaseModel):
    """One row: the school this app runs."""

    name = models.CharField(max_length=120, blank=True)
    # The season whose timing is in use; blank until the Principal chooses.
    active_season = models.CharField(max_length=10, choices=SEASON_CHOICES, blank=True)


class SeasonTiming(BaseModel):
    season = models.CharField(max_length=10, choices=SEASON_CHOICES, unique=True)
    opens_at = models.TimeField()
    closes_at = models.TimeField()


class SchoolPeriod(BaseModel):
    timing = models.ForeignKey(SeasonTiming, on_delete=models.CASCADE, related_name="periods")
    number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=60, blank=True)
    starts_at = models.TimeField()
    ends_at = models.TimeField()

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(fields=["timing", "number"], name="one_period_per_number")
        ]


class Holiday(BaseModel):
    name = models.CharField(max_length=120)
    starts_on = models.DateField(db_index=True)
    ends_on = models.DateField()

    class Meta:
        ordering = ["starts_on"]


class Notice(BaseModel):
    kind = models.CharField(
        max_length=20, choices=[(k.value, k.value.title()) for k in NoticeKind]
    )
    title = models.CharField(max_length=150)
    body = models.TextField()
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
