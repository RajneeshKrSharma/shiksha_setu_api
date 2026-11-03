from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

from apps.core.data.base_model import BaseModel

from ..domain.fuel import BillStatus, FuelType

FUEL_CHOICES = [(f.value, f.value.title()) for f in FuelType]
STATUS_CHOICES = [(s.value, s.value.title()) for s in BillStatus]


class StaffProfile(BaseModel):
    """What the school keeps about a staff member besides their sign-in account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile"
    )
    job_title = models.CharField(max_length=60)


class Van(BaseModel):
    name = models.CharField(max_length=60)
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="driven_vans",
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), condition=models.Q(is_active=True),
                name="one_active_van_per_name",
            ),
            models.UniqueConstraint(
                fields=["driver"],
                condition=models.Q(is_active=True, driver__isnull=False),
                name="one_active_van_per_driver",
            ),
        ]


class FuelBill(BaseModel):
    van = models.ForeignKey(Van, on_delete=models.PROTECT, related_name="fuel_bills")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    payee = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    billed_on = models.DateField(db_index=True)
    fuel = models.CharField(max_length=10, choices=FUEL_CHOICES)
    litres = models.DecimalField(max_digits=6, decimal_places=2)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    odometer_km = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=BillStatus.PENDING.value)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    decided_on = models.DateField(null=True, blank=True)
    reject_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-billed_on", "-odometer_km"]
