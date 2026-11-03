from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import ReadByAnyoneWriteWith
from apps.accounts.domain.capabilities import MANAGE_SCHOOL, POST_NOTICES
from apps.core.domain.errors import NotFound, RuleViolation
from config.container import container

from ..domain.entities import NoticeKind, Season
from .serializers import (
    HolidayCreateInput,
    HolidayOut,
    HolidayPatchInput,
    NoticeInput,
    NoticeOut,
    SchoolOut,
    SchoolPatchInput,
    SeasonScheduleInput,
    SeasonScheduleOut,
    TimingsOut,
)


class _SchoolRights(APIView):
    permission_classes = [ReadByAnyoneWriteWith.of(MANAGE_SCHOOL)]


class SchoolView(_SchoolRights):
    def get(self, request):
        return Response(SchoolOut(container.get_school().call()).data)

    def patch(self, request):
        data = SchoolPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        season = data.validated_data.get("active_season")
        school = container.update_school().call(
            container.actor(request.user),
            name=data.validated_data.get("school_name"),
            active_season=Season(season) if season else None,
        )
        return Response(SchoolOut(school).data)


class TimingsView(_SchoolRights):
    def get(self, request):
        return Response(TimingsOut(container.get_timings().call()).data)


class SeasonScheduleView(_SchoolRights):
    def put(self, request, season):
        try:
            wanted = Season(season)
        except ValueError:
            raise NotFound("There is no such season.")
        data = SeasonScheduleInput(data=request.data)
        data.is_valid(raise_exception=True)
        periods = [
            (p["name"], p["starts_at"], p["ends_at"]) for p in data.validated_data["periods"]
        ]
        schedule = container.set_season_schedule().call(
            container.actor(request.user),
            season=wanted,
            opens_at=data.validated_data["opens_at"],
            closes_at=data.validated_data["closes_at"],
            periods=periods,
        )
        return Response(SeasonScheduleOut(schedule).data)


class HolidayListCreateView(_SchoolRights):
    def get(self, request):
        holidays = container.list_holidays().call(
            from_date=self._date(request, "from"), to_date=self._date(request, "to")
        )
        return Response(HolidayOut(holidays, many=True).data)

    def post(self, request):
        data = HolidayCreateInput(data=request.data)
        data.is_valid(raise_exception=True)
        holiday = container.add_holiday().call(container.actor(request.user), **data.validated_data)
        return Response(HolidayOut(holiday).data, status=201)

    @staticmethod
    def _date(request, name):
        raw = request.query_params.get(name)
        return serializers.DateField().run_validation(raw) if raw else None


class HolidayDetailView(_SchoolRights):
    def patch(self, request, holiday_id):
        data = HolidayPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        holiday = container.update_holiday().call(
            container.actor(request.user), holiday_id, **data.validated_data
        )
        return Response(HolidayOut(holiday).data)

    def delete(self, request, holiday_id):
        container.remove_holiday().call(container.actor(request.user), holiday_id)
        return Response(status=204)


class _NoticeRights(APIView):
    permission_classes = [ReadByAnyoneWriteWith.of(POST_NOTICES)]


class NoticeListCreateView(_NoticeRights):
    def get(self, request):
        kind = request.query_params.get("kind")
        try:
            wanted = NoticeKind(kind) if kind else None
        except ValueError:
            raise RuleViolation("kind must be notice or announcement.",
                                errors={"kind": ["Not a valid kind."]})
        raw_limit = request.query_params.get("limit")
        limit = (
            serializers.IntegerField(min_value=1, max_value=200).run_validation(raw_limit)
            if raw_limit else 50
        )
        notices = container.list_notices().call(kind=wanted, limit=limit)
        return Response(NoticeOut(notices, many=True).data)

    def post(self, request):
        data = NoticeInput(data=request.data)
        data.is_valid(raise_exception=True)
        notice = container.post_notice().call(
            container.actor(request.user),
            kind=NoticeKind(data.validated_data["kind"]),
            title=data.validated_data["title"],
            body=data.validated_data["body"],
        )
        return Response(NoticeOut(notice).data, status=201)


class NoticeDetailView(_NoticeRights):
    def delete(self, request, notice_id):
        container.withdraw_notice().call(container.actor(request.user), notice_id)
        return Response(status=204)
