"""The one place that decides which implementation sits behind each interface.
Use cases receive abstractions; this file hands them the real ones."""
from django.conf import settings

from apps.accounts.data.adapters import DjangoAuthenticator, DjangoPasswordPolicy, JwtTokenIssuer
from apps.accounts.data.repositories import DjangoGrantRepository, DjangoUserRepository, UserMapper
from apps.accounts.domain.capabilities import CapabilityCatalog
from apps.accounts.domain.entities import UserAccount
from apps.accounts.domain.policies import PolicyRegistry
from apps.accounts.domain.services import Authorizer
from apps.accounts.domain.usecases.bootstrap_principal import BootstrapPrincipal
from apps.accounts.domain.usecases.change_password import ChangePassword
from apps.accounts.domain.usecases.create_account import CreateAccount
from apps.accounts.domain.usecases.get_current_user import GetCurrentUser
from apps.accounts.domain.usecases.grant_permission import GrantPermission
from apps.accounts.domain.usecases.list_capabilities import ListCapabilities
from apps.accounts.domain.usecases.list_grants import ListGrants
from apps.accounts.domain.usecases.login import Login
from apps.accounts.domain.usecases.refresh_session import RefreshSession
from apps.accounts.domain.usecases.revoke_permission import RevokePermission
from apps.accounts.domain.usecases.update_my_name import UpdateMyName
from apps.accounts.domain.usecases.vice_principal import (
    GetVicePrincipal,
    ListVicePrincipals,
    RemoveVicePrincipal,
    UpdateVicePrincipal,
)
from apps.core.security.audit_log import DatabaseAuditLogger
from apps.core.data.clock import SystemClock
from apps.core.domain.usecases.member_crud import (
    AddMember,
    DeactivateMember,
    GetMember,
    UpdateMember,
)
from apps.school.data.repositories import (
    DjangoHolidayRepository,
    DjangoNoticeRepository,
    DjangoScheduleRepository,
    DjangoSchoolRepository,
)
from apps.school.domain.usecases.get_school import GetSchool
from apps.school.domain.usecases.get_timings import GetTimings
from apps.school.domain.usecases.holidays import AddHoliday, ListHolidays, RemoveHoliday, UpdateHoliday
from apps.school.domain.usecases.notices import ListNotices, PostNotice, WithdrawNotice
from apps.school.domain.usecases.set_season_schedule import SetSeasonSchedule
from apps.school.domain.usecases.update_school import UpdateSchool
from apps.analytics.domain.usecases.school import (
    GetFuelReport,
    GetLessonCoverage,
    GetPaymentsReport,
    GetStaffAttendance,
)
from apps.analytics.domain.usecases.students import (
    GetExamAverages,
    GetFeeReport,
    GetStudentAttendance,
)
from apps.attendance.data.repositories import (
    DjangoStudentMarkRepository,
    DjangoWorkAttendanceRepository,
)
from apps.attendance.domain.services import AttendingPeople, ClassScope, DayStatusRule, SchoolHours
from apps.attendance.domain.usecases.students import (
    GetClassAttendance,
    MarkStudentAttendance,
    StudentAttendanceReport,
)
from apps.attendance.domain.usecases.work import (
    CheckIn,
    CheckOut,
    CorrectWorkAttendance,
    GetDayBoard,
    ListMyAttendance,
    ListWorkRecords,
)
from apps.exams.data.repositories import (
    DjangoExamRepository,
    DjangoExamSettingsRepository,
    DjangoMarkRepository,
    DjangoPaperRepository,
    DjangoQuestionRepository,
    DjangoUnitRepository,
)
from apps.exams.domain.services import BankScope, ExamScope, ResultBuilder
from apps.exams.domain.usecases.bank import (
    AddQuestion,
    AddUnit,
    ListQuestions,
    ListUnits,
    RemoveQuestion,
    RemoveUnit,
    RenameUnit,
    UpdateQuestion,
)
from apps.exams.domain.usecases.exams import CancelExam, ListExams, ScheduleExam, UpdateExam
from apps.exams.domain.usecases.marks import EnterMarks
from apps.exams.domain.usecases.papers import (
    ApprovePaper,
    ComposePaper,
    GetPaper,
    ListPapers,
    RejectPaper,
    SendPaper,
)
from apps.exams.domain.usecases.results import GetExamResults, GetStudentResults
from apps.exams.domain.usecases.timetable import (
    GetExamSettings,
    ScheduleTimetable,
    UpdateExamSettings,
)
from apps.payments.data.repositories import DjangoPaymentRepository, DjangoSalaryRepository
from apps.payments.domain.policies import PayableKinds, PayeePolicies
from apps.payments.domain.services import PayeeAccess
from apps.payments.domain.services import StatementBuilder as PayStatementBuilder
from apps.payments.domain.usecases.pay import ListPayments, RecordPayment
from apps.payments.domain.usecases.salaries import GetSalaryHistory, SetSalary
from apps.payments.domain.usecases.statements import GetMyAccount, GetPersonAccount, ListPayees
from apps.requests.data.repositories import DjangoRequestRepository
from apps.requests.domain.services import ApprovedLeaves, RequestVisibility
from apps.requests.domain.usecases.requests import (
    ApproveRequest,
    ListRequests,
    RaiseLeave,
    RaiseMeetingQuery,
    RejectRequest,
    WithdrawRequest,
)
from apps.staff.data.repositories import (
    DjangoFuelBillRepository,
    DjangoStaffRepository,
    DjangoVanRepository,
)
from apps.staff.domain.fuel import FuelEstimator
from apps.staff.domain.services import DrivingRule, FleetScope, FuelReporter
from apps.staff.domain.usecases.fuel_bills import (
    ApproveFuelBill,
    ListFuelBills,
    RejectFuelBill,
    SubmitFuelBill,
    WithdrawFuelBill,
)
from apps.staff.domain.usecases.staff import (
    AddStaff,
    GetStaff,
    ListStaff,
    RemoveStaff,
    UpdateStaff,
)
from apps.staff.domain.usecases.vans import AddVan, ListVans, RemoveVan, UpdateVan
from apps.teachers.data.repositories import (
    DjangoAllotmentRepository,
    DjangoLessonRepository,
    DjangoTeacherRepository,
)
from apps.teachers.domain.services import AllotmentClassAccess, TeachingScope
from apps.teachers.domain.usecases.allotments import AllotClass, ListAllotments, RemoveAllotment
from apps.teachers.domain.usecases.lessons import LessonBoard, ListLessons, RecordLesson, ReviseLesson
from apps.teachers.domain.usecases.teachers import (
    AddTeacher,
    GetTeacher,
    ListTeachers,
    RemoveTeacher,
    UpdateTeacher,
)
from apps.students.data.repositories import (
    DjangoAccessoryIssueRepository,
    DjangoAccessoryItemRepository,
    DjangoClassRepository,
    DjangoFeePaymentRepository,
    DjangoFeeStructureRepository,
    DjangoStudentRepository,
)
from apps.students.domain.fees import FeeCalculator, HeadPolicies
from apps.students.domain.services import StatementBuilder
from apps.students.domain.usecases.accessories import (
    AddAccessoryItem,
    IssueAccessory,
    ListAccessoryIssues,
    ListAccessoryItems,
    RemoveAccessoryItem,
    UpdateAccessoryItem,
)
from apps.students.domain.usecases.classes import (
    AddClass,
    GetClass,
    ListClasses,
    RemoveClass,
    UpdateClass,
)
from apps.students.domain.usecases.fees import (
    GetFeeStructure,
    GetStudentFees,
    ListFeeAccounts,
    ListFeePayments,
    ReceiveFeePayment,
    SetFeeAmount,
)
from apps.students.domain.usecases.students import (
    AddStudent,
    GetStudent,
    ListStudents,
    RemoveStudent,
    UpdateStudent,
)



class Container:
    def __init__(self):
        self._catalog = CapabilityCatalog.default()
        self._policies = PolicyRegistry.default(self._catalog)
        self._mapper = UserMapper()
        self._passwords = DjangoPasswordPolicy()
        self._tokens = JwtTokenIssuer()
        self._audit = DatabaseAuditLogger()
        self._clock = SystemClock()
        self._head_policies = HeadPolicies.default()

    # building blocks
    def users(self) -> DjangoUserRepository:
        return DjangoUserRepository(self._mapper)

    def grants(self) -> DjangoGrantRepository:
        return DjangoGrantRepository()

    def authorizer(self) -> Authorizer:
        return Authorizer(self._policies, self.grants(), self._catalog)

    def actor(self, user_row) -> UserAccount:
        """The signed-in person as the domain sees them."""
        return self._mapper.to_entity(user_row)

    # accounts use cases
    def login(self, request) -> Login:
        return Login(DjangoAuthenticator(request, self._mapper), self._tokens)

    def refresh_session(self) -> RefreshSession:
        return RefreshSession(self._tokens)

    def get_current_user(self) -> GetCurrentUser:
        return GetCurrentUser(self.authorizer())

    def update_my_name(self) -> UpdateMyName:
        return UpdateMyName(self.users())

    def change_password(self) -> ChangePassword:
        return ChangePassword(self.users(), self._passwords, self._audit)

    def create_account(self) -> CreateAccount:
        return CreateAccount(
            self.users(), self._policies, self.authorizer(), self._passwords, self._audit
        )

    def bootstrap_principal(self) -> BootstrapPrincipal:
        return BootstrapPrincipal(self.users(), self._passwords, self._audit)

    def grant_permission(self) -> GrantPermission:
        return GrantPermission(
            self.users(), self.grants(), self.authorizer(), self._catalog, self._audit
        )

    def revoke_permission(self) -> RevokePermission:
        return RevokePermission(self.grants(), self.authorizer(), self._audit)

    def list_grants(self) -> ListGrants:
        return ListGrants(self.grants(), self.authorizer())

    def list_capabilities(self) -> ListCapabilities:
        return ListCapabilities(self._catalog)

    def list_vice_principals(self) -> ListVicePrincipals:
        return ListVicePrincipals(self.users(), self.authorizer())

    def get_vice_principal(self) -> GetVicePrincipal:
        return GetVicePrincipal(self.users(), self.authorizer())

    def update_vice_principal(self) -> UpdateVicePrincipal:
        return UpdateVicePrincipal(self.users(), self.grants(), self._passwords,
                                   self.authorizer(), self._audit)

    def remove_vice_principal(self) -> RemoveVicePrincipal:
        return RemoveVicePrincipal(self.users(), self.grants(), self.authorizer(), self._audit)

    # school use cases
    def get_school(self) -> GetSchool:
        return GetSchool(DjangoSchoolRepository())

    def update_school(self) -> UpdateSchool:
        return UpdateSchool(DjangoSchoolRepository(), self.authorizer(), self._audit)

    def get_timings(self) -> GetTimings:
        return GetTimings(DjangoSchoolRepository(), DjangoScheduleRepository())

    def set_season_schedule(self) -> SetSeasonSchedule:
        return SetSeasonSchedule(DjangoScheduleRepository(), self.authorizer(), self._audit)

    def list_holidays(self) -> ListHolidays:
        return ListHolidays(DjangoHolidayRepository())

    def add_holiday(self) -> AddHoliday:
        return AddHoliday(DjangoHolidayRepository(), self.authorizer(), self._audit)

    def update_holiday(self) -> UpdateHoliday:
        return UpdateHoliday(DjangoHolidayRepository(), self.authorizer(), self._audit)

    def remove_holiday(self) -> RemoveHoliday:
        return RemoveHoliday(DjangoHolidayRepository(), self.authorizer(), self._audit)

    def list_notices(self) -> ListNotices:
        return ListNotices(DjangoNoticeRepository())

    def post_notice(self) -> PostNotice:
        return PostNotice(DjangoNoticeRepository(), self.authorizer(), self._audit)

    def withdraw_notice(self) -> WithdrawNotice:
        return WithdrawNotice(DjangoNoticeRepository(), self.authorizer(), self._audit)

    # classes and students
    def class_access(self) -> AllotmentClassAccess:
        return AllotmentClassAccess(self.authorizer(), DjangoAllotmentRepository())

    def list_classes(self) -> ListClasses:
        return ListClasses(DjangoClassRepository(), self.authorizer(), self.class_access())

    def get_class(self) -> GetClass:
        return GetClass(DjangoClassRepository(), self.authorizer(), self.class_access())

    def add_class(self) -> AddClass:
        return AddClass(DjangoClassRepository(), self.authorizer(), self._audit)

    def update_class(self) -> UpdateClass:
        return UpdateClass(DjangoClassRepository(), self.authorizer(), self._audit)

    def remove_class(self) -> RemoveClass:
        return RemoveClass(
            DjangoClassRepository(), DjangoStudentRepository(), self.authorizer(), self._audit
        )

    def list_students(self) -> ListStudents:
        return ListStudents(DjangoStudentRepository(), self.authorizer(), self.class_access())

    def get_student(self) -> GetStudent:
        return GetStudent(GetMember(DjangoStudentRepository()), self.authorizer(),
                          self.class_access())

    def add_student(self) -> AddStudent:
        students = DjangoStudentRepository()
        return AddStudent(AddMember(students), students, DjangoClassRepository(),
                          self.authorizer(), self._audit)

    def update_student(self) -> UpdateStudent:
        students = DjangoStudentRepository()
        return UpdateStudent(GetMember(students), UpdateMember(students), students,
                             DjangoClassRepository(), self.authorizer(), self._audit)

    def remove_student(self) -> RemoveStudent:
        return RemoveStudent(DeactivateMember(DjangoStudentRepository()),
                             self.authorizer(), self._audit)

    # dress and books
    def list_accessory_items(self) -> ListAccessoryItems:
        return ListAccessoryItems(DjangoAccessoryItemRepository(), self.authorizer(), self._audit)

    def add_accessory_item(self) -> AddAccessoryItem:
        return AddAccessoryItem(DjangoAccessoryItemRepository(), DjangoClassRepository(),
                                self.authorizer(), self._audit)

    def update_accessory_item(self) -> UpdateAccessoryItem:
        return UpdateAccessoryItem(DjangoAccessoryItemRepository(), DjangoClassRepository(),
                                   self.authorizer(), self._audit)

    def remove_accessory_item(self) -> RemoveAccessoryItem:
        return RemoveAccessoryItem(DjangoAccessoryItemRepository(), self.authorizer(), self._audit)

    def issue_accessory(self) -> IssueAccessory:
        return IssueAccessory(DjangoAccessoryItemRepository(), DjangoAccessoryIssueRepository(),
                              DjangoStudentRepository(), self.authorizer(), self._audit,
                              self._clock)

    def list_accessory_issues(self) -> ListAccessoryIssues:
        return ListAccessoryIssues(DjangoAccessoryIssueRepository(), self.authorizer())

    # fees
    def _statements(self) -> StatementBuilder:
        return StatementBuilder(
            DjangoFeeStructureRepository(), DjangoAccessoryIssueRepository(),
            DjangoFeePaymentRepository(), FeeCalculator(self._head_policies),
        )

    def get_fee_structure(self) -> GetFeeStructure:
        return GetFeeStructure(DjangoClassRepository(), DjangoFeeStructureRepository(),
                               self._head_policies, self.authorizer())

    def set_fee_amount(self) -> SetFeeAmount:
        return SetFeeAmount(DjangoClassRepository(), DjangoFeeStructureRepository(),
                            self._head_policies, self.authorizer(), self._audit)

    def list_fee_accounts(self) -> ListFeeAccounts:
        return ListFeeAccounts(DjangoStudentRepository(), self._statements(), self.authorizer())

    def get_student_fees(self) -> GetStudentFees:
        return GetStudentFees(DjangoStudentRepository(), self._statements(),
                              DjangoFeePaymentRepository(), self.authorizer())

    def receive_fee_payment(self) -> ReceiveFeePayment:
        return ReceiveFeePayment(DjangoStudentRepository(), self._statements(),
                                 DjangoFeePaymentRepository(), self.authorizer(), self._audit,
                                 self._clock)

    def list_fee_payments(self) -> ListFeePayments:
        return ListFeePayments(DjangoFeePaymentRepository(), self.authorizer())

    # teachers
    def _teachers(self) -> DjangoTeacherRepository:
        return DjangoTeacherRepository(self.users())

    def list_teachers(self) -> ListTeachers:
        return ListTeachers(self._teachers(), self.authorizer())

    def get_teacher(self) -> GetTeacher:
        return GetTeacher(GetMember(self._teachers()), self.authorizer())

    def add_teacher(self) -> AddTeacher:
        return AddTeacher(self.create_account())

    def update_teacher(self) -> UpdateTeacher:
        teachers = self._teachers()
        return UpdateTeacher(GetMember(teachers), UpdateMember(teachers), self.users(),
                             self._passwords, self.authorizer(), self._audit)

    def remove_teacher(self) -> RemoveTeacher:
        return RemoveTeacher(DeactivateMember(self._teachers()), self.authorizer(), self._audit)

    def _teaching_scope(self) -> TeachingScope:
        return TeachingScope(self.authorizer())

    def list_allotments(self) -> ListAllotments:
        return ListAllotments(DjangoAllotmentRepository(), self._teaching_scope())

    def allot_class(self) -> AllotClass:
        return AllotClass(DjangoAllotmentRepository(), self.users(), DjangoClassRepository(),
                          self.authorizer(), self._audit)

    def remove_allotment(self) -> RemoveAllotment:
        return RemoveAllotment(DjangoAllotmentRepository(), self.authorizer(), self._audit)

    def record_lesson(self) -> RecordLesson:
        return RecordLesson(DjangoAllotmentRepository(), DjangoLessonRepository(),
                            self.authorizer(), self._clock)

    def revise_lesson(self) -> ReviseLesson:
        return ReviseLesson(DjangoLessonRepository(), self.authorizer())

    def list_lessons(self) -> ListLessons:
        return ListLessons(DjangoLessonRepository(), self._teaching_scope())

    def lesson_board(self) -> LessonBoard:
        return LessonBoard(DjangoAllotmentRepository(), DjangoLessonRepository(),
                           self._teaching_scope(), self._clock)

    # staff, vans and fuel bills
    def _staff(self) -> DjangoStaffRepository:
        return DjangoStaffRepository(self.users())

    def _fleet_scope(self) -> FleetScope:
        return FleetScope(self.authorizer())

    def _fuel_reporter(self) -> FuelReporter:
        return FuelReporter(DjangoFuelBillRepository(), FuelEstimator())

    def list_staff(self) -> ListStaff:
        return ListStaff(self._staff(), self.authorizer())

    def get_staff(self) -> GetStaff:
        return GetStaff(GetMember(self._staff()), self.authorizer())

    def add_staff(self) -> AddStaff:
        return AddStaff(self.create_account(), self._staff())

    def update_staff(self) -> UpdateStaff:
        staff = self._staff()
        return UpdateStaff(GetMember(staff), UpdateMember(staff), self.users(), self._passwords,
                           DrivingRule(DjangoVanRepository()), self.authorizer(), self._audit)

    def remove_staff(self) -> RemoveStaff:
        return RemoveStaff(DeactivateMember(self._staff()), DrivingRule(DjangoVanRepository()),
                           self.authorizer(), self._audit)

    def list_vans(self) -> ListVans:
        return ListVans(DjangoVanRepository(), self._fleet_scope(), self.authorizer())

    def add_van(self) -> AddVan:
        return AddVan(DjangoVanRepository(), self._staff(), self.authorizer(), self._audit)

    def update_van(self) -> UpdateVan:
        return UpdateVan(DjangoVanRepository(), self._staff(), self.authorizer(), self._audit)

    def remove_van(self) -> RemoveVan:
        return RemoveVan(DjangoVanRepository(), self._staff(), self.authorizer(), self._audit)

    def submit_fuel_bill(self) -> SubmitFuelBill:
        return SubmitFuelBill(DjangoFuelBillRepository(), DjangoVanRepository(),
                              self._fuel_reporter(), self.authorizer(), self._audit, self._clock)

    def list_fuel_bills(self) -> ListFuelBills:
        return ListFuelBills(DjangoFuelBillRepository(), self._fuel_reporter(), self.authorizer())

    def approve_fuel_bill(self) -> ApproveFuelBill:
        return ApproveFuelBill(DjangoFuelBillRepository(), self._fuel_reporter(),
                               self.authorizer(), self._audit, self._clock)

    def reject_fuel_bill(self) -> RejectFuelBill:
        return RejectFuelBill(DjangoFuelBillRepository(), self._fuel_reporter(),
                              self.authorizer(), self._audit, self._clock)

    def withdraw_fuel_bill(self) -> WithdrawFuelBill:
        return WithdrawFuelBill(DjangoFuelBillRepository(), self.authorizer())

    # attendance
    def _class_scope(self) -> ClassScope:
        return ClassScope(DjangoClassRepository(), self.authorizer(), self.class_access())

    def _school_hours(self) -> SchoolHours:
        return SchoolHours(DjangoSchoolRepository(), DjangoScheduleRepository(),
                           DjangoHolidayRepository())

    def get_class_attendance(self) -> GetClassAttendance:
        return GetClassAttendance(DjangoStudentRepository(), DjangoStudentMarkRepository(),
                                  self._class_scope(), self.authorizer(), self._clock)

    def mark_student_attendance(self) -> MarkStudentAttendance:
        return MarkStudentAttendance(DjangoStudentRepository(), DjangoStudentMarkRepository(),
                                     self._class_scope(), self.authorizer(), self._clock,
                                     self._audit)

    def student_attendance_report(self) -> StudentAttendanceReport:
        return StudentAttendanceReport(DjangoStudentRepository(), DjangoStudentMarkRepository(),
                                       self._class_scope(), self.authorizer())

    def check_in(self) -> CheckIn:
        return CheckIn(DjangoWorkAttendanceRepository(), self._school_hours(),
                       self.authorizer(), self._clock)

    def check_out(self) -> CheckOut:
        return CheckOut(DjangoWorkAttendanceRepository(), self.authorizer(), self._clock)

    def list_my_attendance(self) -> ListMyAttendance:
        return ListMyAttendance(DjangoWorkAttendanceRepository(), self.authorizer(), self._clock)

    def get_day_board(self) -> GetDayBoard:
        return GetDayBoard(DjangoWorkAttendanceRepository(), AttendingPeople(self.users()),
                           self._school_hours(), ApprovedLeaves(DjangoRequestRepository()),
                           DayStatusRule(), self.authorizer(), self._clock)

    def list_work_records(self) -> ListWorkRecords:
        return ListWorkRecords(DjangoWorkAttendanceRepository(), self.authorizer())

    # exams
    def _exam_scope(self) -> ExamScope:
        return ExamScope(self.authorizer(), DjangoAllotmentRepository())

    def _results(self) -> ResultBuilder:
        return ResultBuilder(DjangoStudentRepository(), DjangoMarkRepository())

    def list_exams(self) -> ListExams:
        return ListExams(DjangoExamRepository(), DjangoPaperRepository(), self._exam_scope(),
                         self.authorizer())

    def schedule_exam(self) -> ScheduleExam:
        return ScheduleExam(DjangoExamRepository(), DjangoPaperRepository(), self._exam_scope(),
                            self.authorizer(), DjangoClassRepository(), DjangoAllotmentRepository(),
                            self._audit)

    def schedule_timetable(self) -> ScheduleTimetable:
        return ScheduleTimetable(DjangoExamRepository(), DjangoPaperRepository(),
                                 self._exam_scope(), DjangoExamSettingsRepository(),
                                 self.authorizer(), DjangoClassRepository(),
                                 DjangoAllotmentRepository(), self._audit)

    def get_exam_settings(self) -> GetExamSettings:
        return GetExamSettings(DjangoExamSettingsRepository(), self.authorizer())

    def update_exam_settings(self) -> UpdateExamSettings:
        return UpdateExamSettings(DjangoExamSettingsRepository(), self.authorizer(), self._audit)

    def update_exam(self) -> UpdateExam:
        return UpdateExam(DjangoExamRepository(), DjangoPaperRepository(), self._exam_scope(),
                          self.authorizer(), DjangoMarkRepository(), self._audit)

    def cancel_exam(self) -> CancelExam:
        return CancelExam(DjangoExamRepository(), DjangoPaperRepository(), self._exam_scope(),
                          self.authorizer(), DjangoMarkRepository(), self._audit)

    def enter_marks(self) -> EnterMarks:
        return EnterMarks(DjangoExamRepository(), DjangoMarkRepository(), DjangoStudentRepository(),
                          self._results(), self._exam_scope(), self.authorizer(), self._audit,
                          self._clock)

    def get_exam_results(self) -> GetExamResults:
        return GetExamResults(DjangoExamRepository(), self._results(), self._exam_scope(),
                              self.authorizer())

    def get_student_results(self) -> GetStudentResults:
        return GetStudentResults(DjangoStudentRepository(), DjangoExamRepository(),
                                 self._results(), self._exam_scope(), self.class_access(),
                                 self.authorizer())

    def _bank_scope(self) -> BankScope:
        return BankScope(self.authorizer())

    def list_units(self) -> ListUnits:
        return ListUnits(DjangoUnitRepository(), self._bank_scope(), self.authorizer())

    def add_unit(self) -> AddUnit:
        return AddUnit(DjangoUnitRepository(), DjangoAllotmentRepository(), self.authorizer())

    def rename_unit(self) -> RenameUnit:
        return RenameUnit(DjangoUnitRepository(), self.authorizer())

    def remove_unit(self) -> RemoveUnit:
        return RemoveUnit(DjangoUnitRepository(), self.authorizer())

    def list_questions(self) -> ListQuestions:
        return ListQuestions(DjangoUnitRepository(), DjangoQuestionRepository(),
                             self._bank_scope(), self.authorizer())

    def add_question(self) -> AddQuestion:
        return AddQuestion(DjangoUnitRepository(), DjangoQuestionRepository(), self.authorizer())

    def update_question(self) -> UpdateQuestion:
        return UpdateQuestion(DjangoUnitRepository(), DjangoQuestionRepository(), self.authorizer())

    def remove_question(self) -> RemoveQuestion:
        return RemoveQuestion(DjangoUnitRepository(), DjangoQuestionRepository(), self.authorizer())

    def get_paper(self) -> GetPaper:
        return GetPaper(DjangoExamRepository(), DjangoPaperRepository(), self._exam_scope(),
                        self.authorizer())

    def list_papers(self) -> ListPapers:
        return ListPapers(DjangoPaperRepository(), self.authorizer())

    def compose_paper(self) -> ComposePaper:
        return ComposePaper(DjangoExamRepository(), DjangoPaperRepository(), self._exam_scope(),
                            self.authorizer(), DjangoUnitRepository(), DjangoQuestionRepository())

    def send_paper(self) -> SendPaper:
        return SendPaper(DjangoExamRepository(), DjangoPaperRepository(), self._exam_scope(),
                         self.authorizer(), self._audit)

    def approve_paper(self) -> ApprovePaper:
        return ApprovePaper(DjangoExamRepository(), DjangoPaperRepository(), self._exam_scope(),
                            self.authorizer(), self._audit, self._clock)

    def reject_paper(self) -> RejectPaper:
        return RejectPaper(DjangoExamRepository(), DjangoPaperRepository(), self._exam_scope(),
                           self.authorizer(), self._audit, self._clock)

    # payments
    def _pay_statements(self) -> PayStatementBuilder:
        return PayStatementBuilder(DjangoSalaryRepository(), DjangoPaymentRepository(),
                                   DjangoFuelBillRepository())

    def _payee_access(self) -> PayeeAccess:
        return PayeeAccess(self.users(), PayeePolicies.default(), self.authorizer())

    def set_salary(self) -> SetSalary:
        return SetSalary(DjangoSalaryRepository(), DjangoPaymentRepository(),
                         self._payee_access(), self._audit)

    def get_salary_history(self) -> GetSalaryHistory:
        return GetSalaryHistory(DjangoSalaryRepository(), self._payee_access())

    def record_payment(self) -> RecordPayment:
        return RecordPayment(DjangoPaymentRepository(), self._pay_statements(),
                             self._payee_access(), PayableKinds.default(), self._audit,
                             self._clock)

    def list_payments(self) -> ListPayments:
        return ListPayments(DjangoPaymentRepository(), self._payee_access())

    def list_payees(self) -> ListPayees:
        return ListPayees(self.users(), self._pay_statements(), self._payee_access(), self._clock)

    def get_person_account(self) -> GetPersonAccount:
        return GetPersonAccount(self._pay_statements(), DjangoPaymentRepository(),
                                self._payee_access(), self._clock)

    def get_my_account(self) -> GetMyAccount:
        return GetMyAccount(self._pay_statements(), DjangoPaymentRepository(),
                            self.authorizer(), self._clock)

    # analytics
    def get_student_attendance(self) -> GetStudentAttendance:
        return GetStudentAttendance(DjangoStudentMarkRepository(), DjangoClassRepository(),
                                    self.authorizer(), self._clock)

    def get_fee_report(self) -> GetFeeReport:
        return GetFeeReport(DjangoFeePaymentRepository(), DjangoStudentRepository(),
                            self._statements(), self.authorizer(), self._clock)

    def get_exam_averages(self) -> GetExamAverages:
        return GetExamAverages(DjangoExamRepository(), self._results(), self.authorizer(),
                               self._clock)

    def get_staff_attendance(self) -> GetStaffAttendance:
        return GetStaffAttendance(
            DjangoWorkAttendanceRepository(), AttendingPeople(self.users()), self._school_hours(),
            ApprovedLeaves(DjangoRequestRepository()), DayStatusRule(), self.authorizer(),
            self._clock,
        )

    def get_payments_report(self) -> GetPaymentsReport:
        return GetPaymentsReport(DjangoPaymentRepository(), self.users(), self._pay_statements(),
                                 self.authorizer(), self._clock)

    def get_fuel_report(self) -> GetFuelReport:
        return GetFuelReport(DjangoFuelBillRepository(), self._fuel_reporter(), self.authorizer(),
                             self._clock)

    def get_lesson_coverage(self) -> GetLessonCoverage:
        return GetLessonCoverage(DjangoAllotmentRepository(), DjangoLessonRepository(),
                                 self._school_hours(), self.authorizer(), self._clock)

    # requests
    def raise_leave(self) -> RaiseLeave:
        return RaiseLeave(DjangoRequestRepository(), self.authorizer(), self._clock)

    def raise_meeting_query(self) -> RaiseMeetingQuery:
        return RaiseMeetingQuery(DjangoRequestRepository(), self.authorizer(), self._clock)

    def list_requests(self) -> ListRequests:
        return ListRequests(DjangoRequestRepository(), RequestVisibility(self.authorizer()))

    def approve_request(self) -> ApproveRequest:
        return ApproveRequest(DjangoRequestRepository(), self.authorizer(), self._audit,
                              self._clock)

    def reject_request(self) -> RejectRequest:
        return RejectRequest(DjangoRequestRepository(), self.authorizer(), self._audit,
                             self._clock)

    def withdraw_request(self) -> WithdrawRequest:
        return WithdrawRequest(DjangoRequestRepository())

    def correct_work_attendance(self) -> CorrectWorkAttendance:
        return CorrectWorkAttendance(DjangoWorkAttendanceRepository(), self.users(),
                                     self._school_hours(), self.authorizer(), self._audit,
                                     self._clock)


container = Container()
