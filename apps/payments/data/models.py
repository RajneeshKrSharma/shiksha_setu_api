from django.conf import settings
from django.db import models

from apps.core.data.base_model import BaseModel

from ..domain.entities import PaymentKind, PaymentMode

MONEY = {"max_digits": 10, "decimal_places": 2}


class SalaryRate(BaseModel):
    """A monthly salary from the first day of a month onwards."""

    person = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="salary_rates"
    )
    effective_from = models.DateField()
    amount = models.DecimalField(**MONEY)
    set_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-effective_from"]
        constraints = [
            models.UniqueConstraint(fields=["person", "effective_from"], name="one_rate_per_month")
        ]


class Payment(BaseModel):
    person = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments_received"
    )
    kind = models.CharField(max_length=10, choices=[(k.value, k.value) for k in PaymentKind])
    amount = models.DecimalField(**MONEY)
    paid_on = models.DateField(db_index=True)
    mode = models.CharField(max_length=10, choices=[(m.value, m.value) for m in PaymentMode])
    note = models.CharField(max_length=200, blank=True)
    # The first day of the month a salary payment is for.
    month = models.DateField(null=True, blank=True)
    fuel_bill = models.ForeignKey(
        "staff.FuelBill", null=True, blank=True, on_delete=models.PROTECT, related_name="payments"
    )
    receipt_number = models.PositiveIntegerField(unique=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-paid_on", "-receipt_number"]
