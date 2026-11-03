from django.contrib import admin

from .models import (
    AccessoryIssue,
    AccessoryItem,
    FeeAmount,
    FeePayment,
    SchoolClass,
    Student,
)


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ("level", "section", "is_active")
    list_filter = ("is_active",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("name", "roll_number", "school_class", "uses_van", "is_active")
    list_filter = ("school_class", "is_active")
    search_fields = ("name", "roll_number")


@admin.register(AccessoryItem)
class AccessoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "price", "school_class", "is_active")
    list_filter = ("kind", "is_active")


class _Ledger(admin.ModelAdmin):
    """Money records are read-only here: they change only through the API."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AccessoryIssue)
class AccessoryIssueAdmin(_Ledger):
    list_display = ("student", "item", "quantity", "unit_price", "issued_on")


@admin.register(FeePayment)
class FeePaymentAdmin(_Ledger):
    list_display = ("receipt_number", "student", "head", "amount", "paid_on")


@admin.register(FeeAmount)
class FeeAmountAdmin(admin.ModelAdmin):
    list_display = ("school_class", "head", "amount")
