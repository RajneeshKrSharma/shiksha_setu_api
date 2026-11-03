"""What can go wrong in the domain. The API layer decides the HTTP status."""


class DomainError(Exception):
    code = "error"
    default_message = "Something went wrong."

    def __init__(self, message: str | None = None, *, code: str | None = None,
                 errors: dict[str, list[str]] | None = None):
        self.message = message or self.default_message
        self.code = code or self.code
        self.errors = errors
        super().__init__(self.message)


class NotFound(DomainError):
    code = "not_found"
    default_message = "Not found."


class Forbidden(DomainError):
    code = "forbidden"
    default_message = "You do not have permission to do this."


class Unauthenticated(DomainError):
    code = "not_authenticated"
    default_message = "Please sign in."


class Locked(DomainError):
    code = "locked_out"
    default_message = "Too many wrong attempts. Please try again later."


class ExternalServiceError(DomainError):
    """A service we depend on (such as the handwriting reader) failed."""

    code = "service_unavailable"
    default_message = "A service this action needs is not available. Try again."


class RuleViolation(DomainError):
    """The input or the action breaks a business rule."""

    code = "rule_violation"
    default_message = "This is not allowed."
