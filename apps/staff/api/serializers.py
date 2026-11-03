from rest_framework import serializers

from ..domain.fuel import FuelReport, FuelType


class StaffInput(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    job_title = serializers.CharField(max_length=60)


class StaffPatchInput(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=120)
    job_title = serializers.CharField(required=False, max_length=60)
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(required=False, max_length=128, trim_whitespace=False)


class StaffOut(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.EmailField()
    job_title = serializers.CharField()
    is_active = serializers.BooleanField()


class VanInput(serializers.Serializer):
    name = serializers.CharField(max_length=60)
    driver_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class VanPatchInput(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=60)
    driver_id = serializers.UUIDField(required=False, allow_null=True)


class VanOut(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    driver_id = serializers.UUIDField(allow_null=True)
    driver_name = serializers.CharField()


class FuelBillInput(serializers.Serializer):
    van_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    billed_on = serializers.DateField()
    fuel = serializers.ChoiceField(choices=[f.value for f in FuelType])
    litres = serializers.DecimalField(max_digits=6, decimal_places=2)
    rate = serializers.DecimalField(max_digits=10, decimal_places=2)
    odometer_km = serializers.IntegerField()


class RejectInput(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True)


class FuelBillOut(serializers.Serializer):
    """A bill with its amount and the distance and mileage estimate (null for a van's
    first bill)."""

    def to_representation(self, report: FuelReport):
        bill = report.bill
        return {
            "id": str(bill.id),
            "van_id": str(bill.van_id),
            "van_name": bill.van_name,
            "submitted_by_id": str(bill.submitted_by_id),
            "submitted_by_name": bill.submitted_by_name,
            "billed_on": bill.billed_on.isoformat(),
            "fuel": bill.fuel.value,
            "litres": f"{bill.litres:.2f}",
            "rate": f"{bill.rate:.2f}",
            "amount": f"{bill.amount:.2f}",
            "odometer_km": bill.odometer_km,
            "distance_km": report.distance_km,
            "km_per_litre": None if report.km_per_litre is None else f"{report.km_per_litre:.2f}",
            "status": bill.status.value,
            "decided_by_name": bill.decided_by_name,
            "decided_on": bill.decided_on.isoformat() if bill.decided_on else None,
            "reject_reason": bill.reject_reason,
        }
