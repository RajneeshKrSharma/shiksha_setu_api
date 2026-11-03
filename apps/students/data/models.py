from django.conf import settings
from django.db import models

from apps.core.data.base_model import BaseModel

from ..domain.accessories import AccessoryKind
from ..domain.entities import ClassLevel
from ..domain.fees import FeeHead

LEVEL_CHOICES = [(level.value, level.label) for level in ClassLevel]
KIND_CHOICES = [(kind.value, kind.value.title()) for kind in AccessoryKind]
HEAD_CHOICES = [(head.value, head.label) for head in FeeHead]
MONEY = {"max_digits": 10, "decimal_places": 2}


class SchoolClass(BaseModel):
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    section = models.CharField(max_length=3, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["level", "section"],
                condition=models.Q(is_active=True),
                name="one_active_class_per_level_section",
            )
        ]


class Student(BaseModel):
    name = models.CharField(max_length=120)
    roll_number = models.CharField(max_length=10)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT, related_name="students")
    guardian_name = models.CharField(max_length=120)
    uses_van = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["school_class", "roll_number"],
                condition=models.Q(is_active=True),
                name="one_active_roll_number_per_class",
            )
        ]


class AccessoryItem(BaseModel):
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    name = models.CharField(max_length=80)
    price = models.DecimalField(**MONEY)
    # Null: sold to every class.
    school_class = models.ForeignKey(
        SchoolClass, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        ordering = ["kind", "name"]


class AccessoryIssue(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="issues")
    item = models.ForeignKey(AccessoryItem, on_delete=models.PROTECT, related_name="issues")
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(**MONEY)
    issued_on = models.DateField(db_index=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-issued_on", "-created_at"]


class FeeAmount(BaseModel):
    """What one class is charged for one fee (tuition, van)."""

    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="fee_amounts")
    head = models.CharField(max_length=10, choices=HEAD_CHOICES)
    amount = models.DecimalField(**MONEY)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school_class", "head"], name="one_amount_per_class_head")
        ]


class FeePayment(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="payments")
    head = models.CharField(max_length=10, choices=HEAD_CHOICES)
    amount = models.DecimalField(**MONEY)
    paid_on = models.DateField(db_index=True)
    receipt_number = models.PositiveIntegerField(unique=True)
    note = models.CharField(max_length=200, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-paid_on", "-receipt_number"]
