from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import CapabilityGate
from apps.accounts.domain.capabilities import (
    ALLOT_CLASSES,
    MANAGE_TEACHERS,
    RECORD_DAILY_LESSON,
)
from apps.core.api.query import QueryParams
from config.container import container

from .serializers import (
    AllotmentInput,
    AllotmentOut,
    LessonInput,
    LessonOut,
    LessonPatchInput,
    LessonStatusOut,
    TeacherInput,
    TeacherOut,
    TeacherPatchInput,
)

_BOARD = (MANAGE_TEACHERS, ALLOT_CLASSES)


# --------------------------------------------------------------- teachers
class _TeacherRights(APIView):
    permission_classes = [CapabilityGate.of(read=_BOARD, write=(MANAGE_TEACHERS,))]


class TeacherListCreateView(_TeacherRights):
    def get(self, request):
        query = QueryParams(request)
        teachers = container.list_teachers().call(
            container.actor(request.user), query=query.text("query"), active=query.active()
        )
        return Response(TeacherOut(teachers, many=True).data)

    def post(self, request):
        data = TeacherInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.add_teacher().call(container.actor(request.user), **data.validated_data)
        return Response(TeacherOut(saved).data, status=201)


class TeacherDetailView(_TeacherRights):
    def get(self, request, teacher_id):
        teacher = container.get_teacher().call(container.actor(request.user), teacher_id)
        return Response(TeacherOut(teacher).data)

    def patch(self, request, teacher_id):
        data = TeacherPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.update_teacher().call(
            container.actor(request.user), teacher_id, **data.validated_data
        )
        return Response(TeacherOut(saved).data)

    def delete(self, request, teacher_id):
        container.remove_teacher().call(container.actor(request.user), teacher_id)
        return Response(status=204)


# ------------------------------------------------------------- allotments
class _AllotmentRights(APIView):
    permission_classes = [CapabilityGate.of(
        read=(*_BOARD, RECORD_DAILY_LESSON), write=(ALLOT_CLASSES,)
    )]


class AllotmentListCreateView(_AllotmentRights):
    def get(self, request):
        query = QueryParams(request)
        allotments = container.list_allotments().call(
            container.actor(request.user), teacher_id=query.uuid("teacher_id"),
            class_id=query.uuid("class_id"),
        )
        return Response(AllotmentOut(allotments, many=True).data)

    def post(self, request):
        data = AllotmentInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.allot_class().call(container.actor(request.user), **data.validated_data)
        return Response(AllotmentOut(saved).data, status=201)


class AllotmentDetailView(_AllotmentRights):
    def delete(self, request, allotment_id):
        container.remove_allotment().call(container.actor(request.user), allotment_id)
        return Response(status=204)


# ---------------------------------------------------------------- lessons
class _LessonRights(APIView):
    permission_classes = [CapabilityGate.of(
        read=(*_BOARD, RECORD_DAILY_LESSON), write=(RECORD_DAILY_LESSON,)
    )]


class LessonListCreateView(_LessonRights):
    def get(self, request):
        query = QueryParams(request)
        lessons = container.list_lessons().call(
            container.actor(request.user), teacher_id=query.uuid("teacher_id"),
            class_id=query.uuid("class_id"), from_date=query.date("from"),
            to_date=query.date("to"),
        )
        return Response(LessonOut(lessons, many=True).data)

    def post(self, request):
        data = LessonInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.record_lesson().call(
            container.actor(request.user), allotment_id=data.validated_data["allotment_id"],
            topic=data.validated_data["topic"], taught_on=data.validated_data.get("taught_on"),
        )
        return Response(LessonOut(saved).data, status=201)


class LessonDetailView(_LessonRights):
    def patch(self, request, lesson_id):
        data = LessonPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.revise_lesson().call(
            container.actor(request.user), lesson_id, topic=data.validated_data["topic"]
        )
        return Response(LessonOut(saved).data)


class LessonBoardView(APIView):
    """For the Principal: who has recorded today's lesson and who has not."""

    permission_classes = [CapabilityGate.of(read=_BOARD, write=_BOARD)]

    def get(self, request):
        board = container.lesson_board().call(
            container.actor(request.user), day=QueryParams(request).date("day")
        )
        return Response(LessonStatusOut(board, many=True).data)
