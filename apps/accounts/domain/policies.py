"""What each role may do. A role is a class; the Principal is a Teacher who can
also do everything else, so it extends the Teacher policy."""
from abc import ABC, abstractmethod
from collections.abc import Iterable

from apps.core.domain.errors import RuleViolation

from . import capabilities as caps
from .capabilities import Capability, CapabilityCatalog
from .entities import Role


class RolePolicy(ABC):
    role: Role
    # Only the Vice Principal receives permissions one by one, with a reason.
    accepts_grants = False
    # The permission needed to create an account with this role (None: not creatable).
    creation_right: Capability | None = None

    @abstractmethod
    def own_capabilities(self) -> frozenset[Capability]: ...

    def capabilities(self, granted: Iterable[Capability] = ()) -> frozenset[Capability]:
        own = self.own_capabilities()
        return own | frozenset(granted) if self.accepts_grants else own


class StaffPolicy(RolePolicy):
    role = Role.STAFF
    creation_right = caps.MANAGE_STAFF

    def own_capabilities(self) -> frozenset[Capability]:
        return frozenset({
            caps.RECORD_OWN_ATTENDANCE,
            caps.RAISE_MEETING_QUERY,
            caps.VIEW_OWN_PAYMENTS,
            caps.SUBMIT_FUEL_BILL,
        })


class TeacherPolicy(RolePolicy):
    role = Role.TEACHER
    creation_right = caps.MANAGE_TEACHERS

    def own_capabilities(self) -> frozenset[Capability]:
        return frozenset({
            caps.VIEW_STUDENTS,
            caps.MARK_STUDENT_ATTENDANCE,
            caps.CONDUCT_EXAMS,
            caps.PREPARE_QUESTIONS,
            caps.MANAGE_QUESTION_BANK,
            caps.RECORD_DAILY_LESSON,
            caps.RECORD_OWN_ATTENDANCE,
            caps.RAISE_MEETING_QUERY,
            caps.VIEW_OWN_PAYMENTS,
        })


class VicePrincipalPolicy(RolePolicy):
    role = Role.VICE_PRINCIPAL
    accepts_grants = True
    creation_right = caps.APPOINT_VICE_PRINCIPAL

    def own_capabilities(self) -> frozenset[Capability]:
        return frozenset({
            caps.RECORD_OWN_ATTENDANCE,
            caps.RAISE_MEETING_QUERY,
            caps.VIEW_OWN_PAYMENTS,
        })


class PrincipalPolicy(TeacherPolicy):
    """Teaches like a teacher, and holds every permission there is."""

    role = Role.PRINCIPAL
    creation_right = None

    def __init__(self, catalog: CapabilityCatalog):
        self._catalog = catalog

    def own_capabilities(self) -> frozenset[Capability]:
        return super().own_capabilities() | self._catalog.all()


class PolicyRegistry:
    def __init__(self, policies: Iterable[RolePolicy]):
        self._by_role = {policy.role: policy for policy in policies}

    def for_role(self, role: Role | None) -> RolePolicy:
        policy = self._by_role.get(role)
        if policy is None:
            raise RuleViolation("This role does not exist.", errors={"role": ["Unknown role."]})
        return policy

    @classmethod
    def default(cls, catalog: CapabilityCatalog) -> "PolicyRegistry":
        return cls([
            PrincipalPolicy(catalog),
            VicePrincipalPolicy(),
            TeacherPolicy(),
            StaffPolicy(),
        ])
