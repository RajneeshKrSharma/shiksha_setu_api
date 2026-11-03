"""Django looks for models here; they live in data/models.py."""
from .data.models import (  # noqa: F401
    Exam,
    ExamMark,
    Paper,
    PaperItem,
    Question,
    QuestionUnit,
)
