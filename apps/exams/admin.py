from django.contrib import admin

from .models import Exam, ExamMark, Paper, Question, QuestionUnit


class _Record(admin.ModelAdmin):
    """Read-only here: these change only through the API, which keeps the audit trail."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Exam)
class ExamAdmin(_Record):
    list_display = ("held_on", "school_class", "subject", "exam_type", "max_marks", "is_active")
    list_filter = ("exam_type", "is_active")


@admin.register(QuestionUnit)
class QuestionUnitAdmin(_Record):
    list_display = ("name", "teacher", "school_class", "subject", "is_active")


@admin.register(Question)
class QuestionAdmin(_Record):
    list_display = ("text", "marks", "question_type", "unit")


@admin.register(Paper)
class PaperAdmin(_Record):
    list_display = ("exam", "status", "prepared_by")
    list_filter = ("status",)


@admin.register(ExamMark)
class ExamMarkAdmin(_Record):
    list_display = ("exam", "student", "marks", "absent")
