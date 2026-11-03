"""One error shape for the whole API, so the app can show what the server said.

    {"message": "Wrong email or password.", "code": "invalid_credentials",
     "errors": {"password": ["..."]}}      # "errors" only for field problems
"""
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.domain.errors import (
    DomainError,
    ExternalServiceError,
    Forbidden,
    Locked,
    NotFound,
    RuleViolation,
    Unauthenticated,
)

_FIELD_LABELS = {"new": "New password", "current": "Current password"}

# The first matching class wins, so list the specific ones first.
_STATUS = (
    (NotFound, 404),
    (Forbidden, 403),
    (Unauthenticated, 401),
    (Locked, 429),
    (ExternalServiceError, 502),
    (RuleViolation, 400),
    (DomainError, 400),
)


def _first_message(data) -> str:
    """The first human sentence in whatever DRF put in the error."""
    if isinstance(data, (list, tuple)):
        return _first_message(data[0]) if data else ""
    if isinstance(data, dict):
        for key, value in data.items():
            text = _first_message(value)
            if not text:
                continue
            key = str(key)
            if key in ("detail", "non_field_errors", "message"):
                return text
            label = _FIELD_LABELS.get(key, key.replace("_", " ").capitalize())
            # Messages like "This password is too common." already name the field.
            return text if key in text.lower() else f"{label}: {text}"
        return ""
    return str(data)


def _flatten(value) -> list[str]:
    """Every message under a field, even when the field is a list of items with their own
    errors (such as `marks`)."""
    if isinstance(value, dict):
        return [text for item in value.values() for text in _flatten(item)]
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _flatten(item)]
    return [str(value)]


def _from_domain(exc: DomainError) -> Response:
    status = next(code for klass, code in _STATUS if isinstance(exc, klass))
    body = {"message": exc.message, "code": exc.code}
    if exc.errors:
        body["errors"] = exc.errors
    return Response(body, status=status)


def api_exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return _from_domain(exc)
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    body = {"message": _first_message(data) or "Something went wrong."}
    if isinstance(exc, exceptions.ValidationError) and isinstance(data, dict):
        body["errors"] = {str(k): _flatten(v) for k, v in data.items()}
        body["code"] = "validation_error"
    else:
        body["code"] = getattr(exc, "default_code", "error")
    return Response(body, status=response.status_code, headers=dict(response.items()))
