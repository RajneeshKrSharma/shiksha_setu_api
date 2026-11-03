from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

from apps.core.data.base_model import BaseModel

from ..domain.entities import ExamType, PaperStatus, QuestionType

TYPE_CHOICES = [(t.value, t.value.replace("_", " ").title()) for t in ExamType]
QUESTION_TYPE_CHOICES = [(t.value, t.value.upper() if t.value == "mcq" else t.value.title())
                         for t in QuestionType]
PAPER_STATUS_CHOICES = [(s.value, s.value.title()) for s in PaperStatus]


class Exam(BaseModel):
    exam_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    school_class = models.ForeignKey(
        "students.SchoolClass", on_delete=models.PROTECT, related_name="exams"
    )
    subject = models.CharField(max_length=60)
    held_on = models.DateField(db_index=True)
    max_marks = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["held_on", "subject"]
        constraints = [
            models.UniqueConstraint(
                Lower("subject"), "school_class", "exam_type", "held_on",
                condition=models.Q(is_active=True), name="one_active_exam_per_class_subject_day",
            )
        ]


class QuestionUnit(BaseModel):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    school_class = models.ForeignKey(
        "students.SchoolClass", on_delete=models.PROTECT, related_name="+"
    )
    subject = models.CharField(max_length=60)
    name = models.CharField(max_length=80)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "teacher", "school_class", Lower("subject"), Lower("name"),
                condition=models.Q(is_active=True), name="one_active_unit_per_name",
            )
        ]


class Question(BaseModel):
    unit = models.ForeignKey(QuestionUnit, on_delete=models.PROTECT, related_name="questions")
    text = models.CharField(max_length=1000)
    marks = models.PositiveSmallIntegerField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES)

    class Meta:
        ordering = ["created_at"]


class Paper(BaseModel):
    exam = models.OneToOneField(Exam, on_delete=models.PROTECT, related_name="paper")
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    status = models.CharField(
        max_length=10, choices=PAPER_STATUS_CHOICES, default=PaperStatus.DRAFT.value
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    decided_on = models.DateField(null=True, blank=True)
    decision_note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-updated_at"]


class PaperItem(BaseModel):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="items")
    position = models.PositiveSmallIntegerField()
    question = models.ForeignKey(
        Question, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    text = models.CharField(max_length=1000)
    marks = models.PositiveSmallIntegerField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES)

    class Meta:
        ordering = ["position"]


class ExamMark(BaseModel):
    exam = models.ForeignKey(Exam, on_delete=models.PROTECT, related_name="marks")
    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="exam_marks"
    )
    marks = models.PositiveSmallIntegerField(null=True, blank=True)
    absent = models.BooleanField(default=False)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["exam", "student"], name="one_mark_per_exam_student")
        ]
