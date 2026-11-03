from uuid import UUID

from apps.accounts.domain.capabilities import CONDUCT_EXAMS, SCHEDULE_EXAMS, VIEW_RESULTS
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.services import Authorizer
from apps.core.domain.errors import NotFound
from apps.core.domain.usecase import UseCase
from apps.students.domain.ports import ClassAccess
from apps.students.domain.repositories import StudentRepository

from ..entities import ExamResults, StudentResults
from ..repositories import ExamRepository
from ..services import ExamScope, ResultBuilder

_READERS = (VIEW_RESULTS, SCHEDULE_EXAMS, CONDUCT_EXAMS)


class GetExamResults(UseCase):
    """Every student of the class in one exam. The Principal sees any exam; a teacher the
    exams of their own class and subject."""

    def __init__(self, exams: ExamRepository, results: ResultBuilder, scope: ExamScope,
                 authorizer: Authorizer):
        self._exams = exams
        self._results = results
        self._scope = scope
        self._authorizer = authorizer

    def call(self, actor: UserAccount, exam_id: UUID) -> ExamResults:
        self._authorizer.require_any(actor, *_READERS)
        exam = self._exams.get(exam_id)
        if exam is None or not exam.is_active:
            raise NotFound("This exam was not found.")
        if not self._scope.sees_all(actor):
            self._scope.require_holder(actor, exam)
        return self._results.for_exam(exam)


class GetStudentResults(UseCase):
    """One student's exams. The Principal sees all of them; a teacher sees the exams of the
    subjects they take, for a student of a class they are allotted."""

    def __init__(self, students: StudentRepository, exams: ExamRepository,
                 results: ResultBuilder, scope: ExamScope, access: ClassAccess,
                 authorizer: Authorizer):
        self._students = students
        self._exams = exams
        self._results = results
        self._scope = scope
        self._access = access
        self._authorizer = authorizer

    def call(self, actor: UserAccount, student_id: UUID) -> StudentResults:
        self._authorizer.require_any(actor, *_READERS)
        student = self._students.get(student_id)
        if student is None:
            raise NotFound("This student was not found.")
        exams = self._exams.list(class_id=student.class_id)
        if not self._scope.sees_all(actor):
            visible = self._access.visible_class_ids(actor)
            if visible is not None and student.class_id not in visible:
                raise NotFound("This student was not found.")
            held = self._scope.held_by(actor)
            exams = [e for e in exams if (e.class_id, e.subject.lower()) in held]
        return self._results.for_student(student, exams)
