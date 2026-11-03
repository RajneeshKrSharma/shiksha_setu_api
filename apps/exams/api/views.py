from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import CapabilityGate
from apps.accounts.domain.capabilities import (
    CONDUCT_EXAMS,
    MANAGE_QUESTION_BANK,
    PREPARE_QUESTIONS,
    SCHEDULE_EXAMS,
    VIEW_RESULTS,
)
from apps.core.api.query import QueryParams
from config.container import container

from ..domain.entities import ExamType, PaperStatus, QuestionType
from ..domain.usecases.marks import MarkEntry
from .serializers import (
    ExamInput,
    ExamOut,
    ExamPatchInput,
    ExamResultsOut,
    MarksInput,
    PaperInput,
    PaperOut,
    QuestionInput,
    QuestionOut,
    QuestionPatchInput,
    RejectInput,
    StudentResultsOut,
    UnitInput,
    UnitOut,
    UnitPatchInput,
)

_CONDUCTORS = (CONDUCT_EXAMS, SCHEDULE_EXAMS)
_RESULT_READERS = (VIEW_RESULTS, SCHEDULE_EXAMS, CONDUCT_EXAMS)


def _actor(request):
    return container.actor(request.user)


# ------------------------------------------------------------------ exams
class ExamListCreateView(APIView):
    permission_classes = [CapabilityGate.of(read=_CONDUCTORS, write=(SCHEDULE_EXAMS,))]

    def get(self, request):
        query = QueryParams(request)
        lines = container.list_exams().call(
            _actor(request), class_id=query.uuid("class_id"),
            exam_type=query.choice("type", ExamType), from_date=query.date("from"),
            to_date=query.date("to"),
        )
        return Response(ExamOut(lines, many=True).data)

    def post(self, request):
        data = ExamInput(data=request.data)
        data.is_valid(raise_exception=True)
        fields = dict(data.validated_data, exam_type=ExamType(data.validated_data["exam_type"]))
        return Response(ExamOut(container.schedule_exam().call(_actor(request), **fields)).data,
                        status=201)


class ExamDetailView(APIView):
    permission_classes = [CapabilityGate.of(read=(), write=(SCHEDULE_EXAMS,))]

    def patch(self, request, exam_id):
        data = ExamPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        changes = dict(data.validated_data)
        if "exam_type" in changes:
            changes["exam_type"] = ExamType(changes["exam_type"])
        line = container.update_exam().call(_actor(request), exam_id, **changes)
        return Response(ExamOut(line).data)

    def delete(self, request, exam_id):
        container.cancel_exam().call(_actor(request), exam_id)
        return Response(status=204)


# ----------------------------------------------------------- marks, results
class ExamMarksView(APIView):
    permission_classes = [CapabilityGate.of(read=_RESULT_READERS, write=_CONDUCTORS)]

    def get(self, request, exam_id):
        results = container.get_exam_results().call(_actor(request), exam_id)
        return Response(ExamResultsOut(results).data)

    def put(self, request, exam_id):
        data = MarksInput(data=request.data)
        data.is_valid(raise_exception=True)
        entries = [MarkEntry(m["student_id"], m["marks"], m["absent"]) for m in data.validated_data["marks"]]
        results = container.enter_marks().call(_actor(request), exam_id, entries=entries)
        return Response(ExamResultsOut(results).data)


class StudentResultsView(APIView):
    permission_classes = [CapabilityGate.of(read=_RESULT_READERS, write=())]

    def get(self, request, student_id):
        results = container.get_student_results().call(_actor(request), student_id)
        return Response(StudentResultsOut(results).data)


# ------------------------------------------------------------------ paper
class ExamPaperView(APIView):
    permission_classes = [CapabilityGate.of(
        read=(PREPARE_QUESTIONS, SCHEDULE_EXAMS), write=(PREPARE_QUESTIONS,)
    )]

    def get(self, request, exam_id):
        return Response(PaperOut(container.get_paper().call(_actor(request), exam_id)).data)

    def put(self, request, exam_id):
        data = PaperInput(data=request.data)
        data.is_valid(raise_exception=True)
        paper = container.compose_paper().call(
            _actor(request), exam_id, question_ids=data.validated_data["question_ids"]
        )
        return Response(PaperOut(paper).data)


class PaperSendView(APIView):
    permission_classes = [CapabilityGate.of(read=(), write=(PREPARE_QUESTIONS,))]

    def post(self, request, exam_id):
        return Response(PaperOut(container.send_paper().call(_actor(request), exam_id)).data)


class PaperApproveView(APIView):
    permission_classes = [CapabilityGate.of(read=(), write=(SCHEDULE_EXAMS,))]

    def post(self, request, exam_id):
        return Response(PaperOut(container.approve_paper().call(_actor(request), exam_id)).data)


class PaperRejectView(APIView):
    permission_classes = [CapabilityGate.of(read=(), write=(SCHEDULE_EXAMS,))]

    def post(self, request, exam_id):
        data = RejectInput(data=request.data)
        data.is_valid(raise_exception=True)
        paper = container.reject_paper().call(
            _actor(request), exam_id, reason=data.validated_data["reason"]
        )
        return Response(PaperOut(paper).data)


class PaperListView(APIView):
    permission_classes = [CapabilityGate.of(read=(SCHEDULE_EXAMS,), write=())]

    def get(self, request):
        papers = container.list_papers().call(
            _actor(request), status=QueryParams(request).choice("status", PaperStatus)
        )
        return Response(PaperOut(papers, many=True).data)


# ---------------------------------------------------------- question bank
class UnitListCreateView(APIView):
    permission_classes = [CapabilityGate.of(
        read=(MANAGE_QUESTION_BANK, SCHEDULE_EXAMS, VIEW_RESULTS), write=(MANAGE_QUESTION_BANK,)
    )]

    def get(self, request):
        query = QueryParams(request)
        units = container.list_units().call(
            _actor(request), teacher_id=query.uuid("teacher_id"), class_id=query.uuid("class_id"),
            subject=query.text("subject") or None,
        )
        return Response(UnitOut(units, many=True).data)

    def post(self, request):
        data = UnitInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.add_unit().call(_actor(request), **data.validated_data)
        return Response(UnitOut(saved).data, status=201)


class UnitDetailView(APIView):
    permission_classes = [CapabilityGate.of(read=(), write=(MANAGE_QUESTION_BANK,))]

    def patch(self, request, unit_id):
        data = UnitPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.rename_unit().call(_actor(request), unit_id, name=data.validated_data["name"])
        return Response(UnitOut(saved).data)

    def delete(self, request, unit_id):
        container.remove_unit().call(_actor(request), unit_id)
        return Response(status=204)


class UnitQuestionsView(APIView):
    permission_classes = [CapabilityGate.of(
        read=(MANAGE_QUESTION_BANK, PREPARE_QUESTIONS, SCHEDULE_EXAMS, VIEW_RESULTS),
        write=(PREPARE_QUESTIONS,),
    )]

    def get(self, request, unit_id):
        questions = container.list_questions().call(_actor(request), unit_id)
        return Response(QuestionOut(questions, many=True).data)

    def post(self, request, unit_id):
        data = QuestionInput(data=request.data)
        data.is_valid(raise_exception=True)
        saved = container.add_question().call(
            _actor(request), unit_id, text=data.validated_data["text"],
            marks=data.validated_data["marks"],
            question_type=QuestionType(data.validated_data["question_type"]),
        )
        return Response(QuestionOut(saved).data, status=201)


class QuestionDetailView(APIView):
    permission_classes = [CapabilityGate.of(read=(), write=(PREPARE_QUESTIONS,))]

    def patch(self, request, question_id):
        data = QuestionPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        changes = dict(data.validated_data)
        if "question_type" in changes:
            changes["question_type"] = QuestionType(changes["question_type"])
        saved = container.update_question().call(_actor(request), question_id, **changes)
        return Response(QuestionOut(saved).data)

    def delete(self, request, question_id):
        container.remove_question().call(_actor(request), question_id)
        return Response(status=204)
