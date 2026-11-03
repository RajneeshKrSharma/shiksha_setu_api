"""Everything a person can be allowed to do, taken from the school's feature list.
A new feature adds one line here and, where it belongs, one line in a policy."""
from collections.abc import Iterable
from dataclasses import dataclass

from apps.core.domain.errors import RuleViolation


@dataclass(frozen=True)
class Capability:
    code: str
    label: str
    # False: only the Principal ever has it; it can never be handed to anyone.
    grantable: bool = True


# Only the Principal
GRANT_PERMISSIONS = Capability("grant_permissions", "Give permissions to the Vice Principal", False)
APPOINT_VICE_PRINCIPAL = Capability("appoint_vice_principal", "Appoint a Vice Principal", False)

# School
MANAGE_SCHOOL = Capability("manage_school", "School name, periods, timings and holidays")
POST_NOTICES = Capability("post_notices", "Notices and announcements")

# Students
MANAGE_CLASSES = Capability("manage_classes", "Add, edit and remove classes")
MANAGE_STUDENTS = Capability("manage_students", "Add, edit and remove students")
VIEW_STUDENTS = Capability("view_students", "See classes and students")
MANAGE_ACCESSORIES = Capability("manage_accessories", "Dress and books")
MANAGE_FEES = Capability("manage_fees", "Tuition, dress, books and van fees")
VIEW_RESULTS = Capability("view_results", "Student results")
VIEW_ATTENDANCE = Capability("view_attendance", "Check attendance")
CORRECT_ATTENDANCE = Capability(
    "correct_attendance", "Correct past student attendance and missed check-ins"
)

# Teachers
MANAGE_TEACHERS = Capability("manage_teachers", "Add, edit and remove teachers")
MANAGE_TEACHER_PAYMENTS = Capability("manage_teacher_payments", "Teacher payments")
ALLOT_CLASSES = Capability("allot_classes", "Allot classes to teachers")
SCHEDULE_EXAMS = Capability("schedule_exams", "Exam schedules")

# Staff
MANAGE_STAFF = Capability("manage_staff", "Add, edit and remove staff")
MANAGE_STAFF_PAYMENTS = Capability("manage_staff_payments", "Staff payments")
ALLOT_VANS = Capability("allot_vans", "Allot vans")
APPROVE_FUEL_BILLS = Capability("approve_fuel_bills", "Approve fuel bills and distance estimates")

# Requests
DECIDE_REQUESTS = Capability("decide_requests", "Approve or reject requests")
APPROVE_LEAVES = Capability("approve_leaves", "Approve leaves")

# More
VIEW_ANALYTICS = Capability("view_analytics", "Analysis graphs")

# What a teacher does in the app
MARK_STUDENT_ATTENDANCE = Capability("mark_student_attendance", "Mark student attendance")
CONDUCT_EXAMS = Capability("conduct_exams", "Conduct unit, mid and annual exams")
PREPARE_QUESTIONS = Capability("prepare_questions", "Prepare questions")
MANAGE_QUESTION_BANK = Capability("manage_question_bank", "Question bank set-up")
RECORD_DAILY_LESSON = Capability("record_daily_lesson", "Record today's lesson")

# What a teacher or staff member does for themselves
RECORD_OWN_ATTENDANCE = Capability("record_own_attendance", "Log in and log out time")
RAISE_MEETING_QUERY = Capability("raise_meeting_query", "Ask the Principal for a meeting")
VIEW_OWN_PAYMENTS = Capability("view_own_payments", "See own payments")
SUBMIT_FUEL_BILL = Capability("submit_fuel_bill", "Submit fuel bills")


class CapabilityCatalog:
    def __init__(self, capabilities: Iterable[Capability]):
        self._by_code = {c.code: c for c in capabilities}

    def all(self) -> frozenset[Capability]:
        return frozenset(self._by_code.values())

    def grantable(self) -> list[Capability]:
        return sorted((c for c in self._by_code.values() if c.grantable), key=lambda c: c.code)

    def find(self, code: str) -> Capability | None:
        return self._by_code.get(code)

    def get(self, code: str) -> Capability:
        capability = self.find(code)
        if capability is None:
            raise RuleViolation("This permission does not exist.",
                                errors={"capability": ["Unknown permission."]})
        return capability

    @classmethod
    def default(cls) -> "CapabilityCatalog":
        return cls(
            value for value in globals().values() if isinstance(value, Capability)
        )
