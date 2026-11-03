from django.contrib import admin

from .models import FuelBill, StaffProfile, Van


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "job_title")


@admin.register(Van)
class VanAdmin(admin.ModelAdmin):
    list_display = ("name", "driver", "is_active")
    list_filter = ("is_active",)


@admin.register(FuelBill)
class FuelBillAdmin(admin.ModelAdmin):
    """Bills are read-only here: they change only through the API, where approval is recorded."""

    list_display = ("billed_on", "van", "fuel", "litres", "rate", "odometer_km", "status")
    list_filter = ("status", "fuel")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
