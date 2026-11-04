from rest_framework import serializers

from ..domain.entities import (
    ExamResults,
    ExamSettings,
    ExamType,
    Paper,
    QuestionType,
    SameDayRule,
    StudentResults,
)
from ..domain.services import ExamLine
from ..domain.usecases.timetable import TimetableResult

_EXAM_TYPES = [t.value for t in ExamType]
_QUESTION_TYPES = [t.value for t in QuestionType]


def _hhmm(value) -> str | None:
    return value.strftime("%H:%M") if value else None


# ------------------------------------------------------------------ exams
class ExamInput(serializers.Serializer):
    exam_type = serializers.ChoiceField(choices=_EXAM_TYPES)
    class_id = serializers.UUIDField()
    subject = serializers.CharField(max_length=60)
    held_on = serializers.DateField()
    max_marks = serializers.IntegerField()
    starts_at = serializers.TimeField(required=False, allow_null=True)
    duration_minutes = serializers.IntegerField(required=False, allow_null=True)


class ExamPatchInput(serializers.Serializer):
    exam_type = serializers.ChoiceField(required=False, choices=_EXAM_TYPES)
    held_on = serializers.DateField(required=False)
    max_marks = serializers.IntegerField(required=False)
    starts_at = serializers.TimeField(required=False, allow_null=True)
    duration_minutes = serializers.IntegerField(required=False, allow_null=True)


class ExamOut(serializers.Serializer):
    """An exam with the teacher who takes it and the state of its paper."""

    def to_representation(self, line: ExamLine):
        exam = line.exam
        return {
            "id": str(exam.id),
            "exam_type": exam.exam_type.value,
            "class_id": str(exam.class_id),
            "class_name": exam.class_name,
            "subject": exam.subject,
            "held_on": exam.held_on.isoformat(),
            "max_marks": exam.max_marks,
            "starts_at": _hhmm(exam.starts_at),
            "duration_minutes": exam.duration_minutes,
            "teacher_id": str(line.teacher_id) if line.teacher_id else None,
            "teacher_name": line.teacher_name,
            "paper_status": line.paper_status.value if line.paper_status else None,
        }


# ---------------------------------------------------- timetable and settings
class TimetableEntryInput(serializers.Serializer):
    subject = serializers.CharField(max_length=60)
    held_on = serializers.DateField()
    max_marks = serializers.IntegerField(required=False, allow_null=True)
    starts_at = serializers.TimeField(required=False, allow_null=True)
    duration_minutes = serializers.IntegerField(required=False, allow_null=True)


class TimetableInput(serializers.Serializer):
    exam_type = serializers.ChoiceField(choices=_EXAM_TYPES)
    class_id = serializers.UUIDField()
    entries = TimetableEntryInput(many=True)


class TimetableOut(serializers.Serializer):
    def to_representation(self, result: TimetableResult):
        return {"exams": ExamOut(result.lines, many=True).data, "warnings": result.warnings}


class ExamSettingsInput(serializers.Serializer):
    default_max_marks = serializers.IntegerField()
    default_duration_minutes = serializers.IntegerField()
    default_start_time = serializers.TimeField(allow_null=True)
    show_time = serializers.BooleanField()
    same_day_rule = serializers.ChoiceField(choices=[r.value for r in SameDayRule])
    min_gap_days = serializers.IntegerField()
    off_weekdays = serializers.ListField(child=serializers.IntegerField())
    off_dates = serializers.ListField(child=serializers.DateField())
    type_labels = serializers.DictField(child=serializers.CharField(allow_blank=True))


class ExamSettingsOut(serializers.Serializer):
    def to_representation(self, settings: ExamSettings):
        return {
            "default_max_marks": settings.default_max_marks,
            "default_duration_minutes": settings.default_duration_minutes,
            "default_start_time": _hhmm(settings.default_start_time),
            "show_time": settings.show_time,
            "same_day_rule": settings.same_day_rule.value,
            "min_gap_days": settings.min_gap_days,
            "off_weekdays": settings.off_weekdays,
            "off_dates": [d.isoformat() for d in settings.off_dates],
            "type_labels": {t.value: label for t, label in settings.type_labels.items()},
        }


# ---------------------------------------------------------- question bank
class UnitInput(serializers.Serializer):
    class_id = serializers.UUIDField()
    subject = serializers.CharField(max_length=60)
    name = serializers.CharField(max_length=80)


class UnitPatchInput(serializers.Serializer):
    name = serializers.CharField(max_length=80)


class UnitOut(serializers.Serializer):
    id = serializers.UUIDField()
    teacher_id = serializers.UUIDField()
    teacher_name = serializers.CharField()
    class_id = serializers.UUIDField()
    class_name = serializers.CharField()
    subject = serializers.CharField()
    name = serializers.CharField()


class QuestionInput(serializers.Serializer):
    text = serializers.CharField(max_length=1000)
    marks = serializers.IntegerField()
    question_type = serializers.ChoiceField(choices=_QUESTION_TYPES)


class QuestionPatchInput(serializers.Serializer):
    text = serializers.CharField(required=False, max_length=1000)
    marks = serializers.IntegerField(required=False)
    question_type = serializers.ChoiceField(required=False, choices=_QUESTION_TYPES)


class QuestionOut(serializers.Serializer):
    id = serializers.UUIDField()
    unit_id = serializers.UUIDField()
    text = serializers.CharField()
    marks = serializers.IntegerField()
    question_type = serializers.CharField()


# ------------------------------------------------------------------ paper
class PaperInput(serializers.Serializer):
    question_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=True)


class RejectInput(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True)


class PaperOut(serializers.Serializer):
    def to_representation(self, paper: Paper):
        return {
            "exam_id": str(paper.exam_id),
            "status": paper.status.value,
            "total_marks": paper.total_marks,
            "prepared_by_name": paper.prepared_by_name,
            "decided_on": paper.decided_on.isoformat() if paper.decided_on else None,
            "decision_note": paper.decision_note,
            "questions": [
                {"position": i.position, "question_id": str(i.question_id) if i.question_id else None,
                 "text": i.text, "marks": i.marks, "question_type": i.question_type.value}
                for i in paper.items
            ],
        }


# ------------------------------------------------------- marks and results
class MarkInput(serializers.Serializer):
    student_id = serializers.UUIDField()
    marks = serializers.IntegerField(required=False, allow_null=True, default=None)
    absent = serializers.BooleanField(required=False, default=False)


class MarksInput(serializers.Serializer):
    marks = MarkInput(many=True, allow_empty=True)


def _percent(value) -> str | None:
    return None if value is None else f"{value:.2f}"


class ExamResultsOut(serializers.Serializer):
    def to_representation(self, results: ExamResults):
        exam = results.exam
        return {
            "exam_id": str(exam.id),
            "exam_type": exam.exam_type.value,
            "class_name": exam.class_name,
            "subject": exam.subject,
            "held_on": exam.held_on.isoformat(),
            "max_marks": exam.max_marks,
            "entered": results.entered,
            "absent": results.absent,
            "average": _percent(results.average),
            "highest": results.highest,
            "lowest": results.lowest,
            "students": [
                {
                    "student_id": str(line.student.id),
                    "name": line.student.name,
                    "roll_number": line.student.roll_number,
                    "marks": line.mark.marks if line.mark else None,
                    "absent": bool(line.mark and line.mark.absent),
                    "entered": line.mark is not None,
                    "percentage": _percent(line.percentage),
                }
                for line in results.lines
            ],
        }


class StudentResultsOut(serializers.Serializer):
    def to_representation(self, results: StudentResults):
        student = results.student
        return {
            "student_id": str(student.id),
            "name": student.name,
            "roll_number": student.roll_number,
            "class_name": student.class_name,
            "total_obtained": results.total_obtained,
            "total_out_of": results.total_out_of,
            "percentage": _percent(results.percentage),
            "exams": [
                {
                    "exam_id": str(line.exam.id),
                    "exam_type": line.exam.exam_type.value,
                    "subject": line.exam.subject,
                    "held_on": line.exam.held_on.isoformat(),
                    "max_marks": line.exam.max_marks,
                    "marks": line.mark.marks if line.mark else None,
                    "absent": bool(line.mark and line.mark.absent),
                    "entered": line.mark is not None,
                    "percentage": _percent(line.percentage),
                }
                for line in results.lines
            ],
        }
