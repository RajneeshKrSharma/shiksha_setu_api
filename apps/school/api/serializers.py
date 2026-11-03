from rest_framework import serializers

from ..domain.entities import NoticeKind, Season
from ..domain.usecases.get_timings import Timings

_HHMM = {"format": "%H:%M", "input_formats": ["%H:%M", "%H:%M:%S"]}


class SchoolPatchInput(serializers.Serializer):
    school_name = serializers.CharField(required=False, max_length=120)
    active_season = serializers.ChoiceField(required=False, choices=[s.value for s in Season])


class SchoolOut(serializers.Serializer):
    school_name = serializers.CharField(source="name")
    active_season = serializers.CharField(allow_null=True)


class PeriodInput(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, default="", max_length=60)
    starts_at = serializers.TimeField(**_HHMM)
    ends_at = serializers.TimeField(**_HHMM)


class SeasonScheduleInput(serializers.Serializer):
    opens_at = serializers.TimeField(**_HHMM)
    closes_at = serializers.TimeField(**_HHMM)
    periods = PeriodInput(many=True, allow_empty=True)


class PeriodOut(serializers.Serializer):
    number = serializers.IntegerField()
    name = serializers.CharField()
    starts_at = serializers.TimeField(**_HHMM)
    ends_at = serializers.TimeField(**_HHMM)


class SeasonScheduleOut(serializers.Serializer):
    season = serializers.CharField()
    opens_at = serializers.TimeField(**_HHMM)
    closes_at = serializers.TimeField(**_HHMM)
    periods = PeriodOut(many=True)


class TimingsOut(serializers.Serializer):
    """Every season is listed; a season not set yet has null hours and no periods."""

    def to_representation(self, timings: Timings):
        seasons = []
        for season, schedule in timings.by_season.items():
            if schedule is None:
                seasons.append(
                    {"season": season.value, "opens_at": None, "closes_at": None, "periods": []}
                )
            else:
                seasons.append(SeasonScheduleOut(schedule).data)
        return {
            "active_season": timings.active_season.value if timings.active_season else None,
            "seasons": seasons,
        }


class HolidayCreateInput(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    starts_on = serializers.DateField()
    ends_on = serializers.DateField(required=False)


class HolidayPatchInput(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=120)
    starts_on = serializers.DateField(required=False)
    ends_on = serializers.DateField(required=False)


class HolidayOut(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()


class NoticeInput(serializers.Serializer):
    kind = serializers.ChoiceField(choices=[k.value for k in NoticeKind], default=NoticeKind.NOTICE.value)
    title = serializers.CharField(max_length=150)
    body = serializers.CharField(max_length=2000)


class NoticeOut(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    title = serializers.CharField()
    body = serializers.CharField()
    posted_by_id = serializers.UUIDField(allow_null=True)
    posted_by_name = serializers.CharField()
    posted_at = serializers.DateTimeField()
