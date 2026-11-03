from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from apps.accounts.domain.capabilities import VIEW_OWN_PAYMENTS
from apps.accounts.domain.entities import Role, UserAccount
from apps.accounts.domain.repositories import UserRepository
from apps.accounts.domain.services import Authorizer
from apps.core.domain.clock import Clock
from apps.core.domain.errors import Forbidden
from apps.core.domain.usecase import UseCase

from ..entities import Payment, PayeeSummary, Statement
from ..repositories import PaymentRepository
from ..services import PayeeAccess, StatementBuilder


@dataclass(frozen=True)
class PersonAccount:
    """A person with what they are owed and everything paid to them."""

    person: UserAccount
    current_salary: Decimal | None
    statement: Statement
    payments: list[Payment]


class ListPayees(UseCase):
    """The teachers and staff the actor may pay, with what each is owed."""

    def __init__(self, users: UserRepository, statements: StatementBuilder, access: PayeeAccess,
                 clock: Clock):
        self._users = users
        self._statements = statements
        self._access = access
        self._clock = clock

    def call(self, actor: UserAccount, *, role: Role | None = None, query: str = "",
             active: bool | None = True) -> list[PayeeSummary]:
        managed = self._access.managed_roles(actor)
        if not managed:
            raise Forbidden()
        if role is not None and role not in {p.role for p in managed}:
            raise Forbidden()
        today = self._clock.today()
        roles = [p.role for p in managed if role is None or p.role == role]
        return [
            PayeeSummary(
                person_id=person.id, name=person.name, role=person.role.value,
                current_salary=self._statements.current_salary(person.id, today),
                statement=self._statements.build(person.id, today),
            )
            for r in roles
            for person in self._users.list(role=r, query=query.strip(), active=active)
        ]


class _AccountView(UseCase):
    def __init__(self, statements: StatementBuilder, payments: PaymentRepository, clock: Clock):
        self._statements = statements
        self._payments = payments
        self._clock = clock

    def _account(self, person: UserAccount) -> PersonAccount:
        today = self._clock.today()
        return PersonAccount(
            person=person, current_salary=self._statements.current_salary(person.id, today),
            statement=self._statements.build(person.id, today),
            payments=self._payments.list(person_id=person.id),
        )


class GetPersonAccount(_AccountView):
    def __init__(self, statements: StatementBuilder, payments: PaymentRepository,
                 access: PayeeAccess, clock: Clock):
        super().__init__(statements, payments, clock)
        self._access = access

    def call(self, actor: UserAccount, person_id: UUID) -> PersonAccount:
        person, policy = self._access.payee(person_id)
        self._access.require_view(actor, person, policy)
        return self._account(person)


class GetMyAccount(_AccountView):
    def __init__(self, statements: StatementBuilder, payments: PaymentRepository,
                 authorizer: Authorizer, clock: Clock):
        super().__init__(statements, payments, clock)
        self._authorizer = authorizer

    def call(self, actor: UserAccount) -> PersonAccount:
        self._authorizer.require(actor, VIEW_OWN_PAYMENTS)
        return self._account(actor)
