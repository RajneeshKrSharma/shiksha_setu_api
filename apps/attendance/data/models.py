from django.conf import settings
from django.db import models

from apps.core.data.base_model import BaseModel

from ..domain.entities import StudentStatus, WorkStatus

STUDENT_STATUS_CHOICES = [(s.value, s.value.title()) for s in StudentStatus]
WORK_STATUS_CHOICES = [(s.value, s.value.title()) for s in WorkStatus]


class StudentAttendance(BaseModel):
    """One student on one day."""

    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="attendance"
    )
    school_class = models.ForeignKey(
        "students.SchoolClass", on_delete=models.PROTECT, related_name="+"
    )
    day = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=STUDENT_STATUS_CHOICES)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "day"], name="one_mark_per_student_day")
        ]


class WorkAttendance(BaseModel):
    """A teacher's or staff member's day: login and logout time."""

    person = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="work_attendance"
    )
    day = models.DateField(db_index=True)
    checked_in_at = models.TimeField()
    checked_out_at = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=WORK_STATUS_CHOICES)
    corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ["-day"]
        constraints = [
            models.UniqueConstraint(fields=["person", "day"], name="one_record_per_person_day")
        ]
