"""Django looks for models here; they live in data/models.py."""
from .data.models import (  # noqa: F401
    Exam,
    ExamMark,
    ExamSettings,
    Paper,
    PaperItem,
    Question,
    QuestionUnit,
)
