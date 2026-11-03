from django.contrib import admin

from .models import Holiday, Notice, School, SchoolPeriod, SeasonTiming


class SchoolPeriodInline(admin.TabularInline):
    model = SchoolPeriod
    extra = 0


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "active_season")


@admin.register(SeasonTiming)
class SeasonTimingAdmin(admin.ModelAdmin):
    list_display = ("season", "opens_at", "closes_at")
    inlines = [SchoolPeriodInline]


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ("name", "starts_on", "ends_on", "is_active")
    list_filter = ("is_active",)


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "posted_by", "created_at", "is_active")
    list_filter = ("kind", "is_active")
