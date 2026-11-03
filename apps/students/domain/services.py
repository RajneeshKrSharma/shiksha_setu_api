from .entities import Student
from .fees import FeeCalculator, FeeContext, FeeStatement
from .repositories import AccessoryIssueRepository, FeePaymentRepository, FeeStructureRepository


class StatementBuilder:
    """Puts together what one student owes and has paid, from the class's fee amounts,
    the items sold to them and their payments."""

    def __init__(self, structure: FeeStructureRepository, issues: AccessoryIssueRepository,
                 payments: FeePaymentRepository, calculator: FeeCalculator):
        self._structure = structure
        self._issues = issues
        self._payments = payments
        self._calculator = calculator

    def build(self, student: Student) -> FeeStatement:
        context = FeeContext(
            amounts=self._structure.amounts_for(student.class_id),
            sold=self._issues.total_sold(student.id),
        )
        return self._calculator.statement(student, context, self._payments.total_paid(student.id))
