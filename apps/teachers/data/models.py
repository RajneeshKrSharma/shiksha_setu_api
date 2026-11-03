from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

from apps.core.data.base_model import BaseModel


class Allotment(BaseModel):
    """A class and subject given to a teacher (the Principal can be one too)."""

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="allotments"
    )
    school_class = models.ForeignKey(
        "students.SchoolClass", on_delete=models.PROTECT, related_name="allotments"
    )
    subject = models.CharField(max_length=60)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("subject"), "school_class",
                condition=models.Q(is_active=True),
                name="one_active_allotment_per_class_subject",
            )
        ]


class Lesson(BaseModel):
    """What was taught in one allotment on one day."""

    allotment = models.ForeignKey(Allotment, on_delete=models.PROTECT, related_name="lessons")
    # Copied at the time, so renaming nothing later changes what the record says.
    subject = models.CharField(max_length=60)
    taught_on = models.DateField(db_index=True)
    topic = models.CharField(max_length=500)

    class Meta:
        ordering = ["-taught_on", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["allotment", "taught_on"], name="one_lesson_per_day")
        ]
