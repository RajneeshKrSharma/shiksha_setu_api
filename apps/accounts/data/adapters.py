"""The framework pieces behind the domain's ports: Django passwords and sign-in,
django-axes lockout, and JWT tokens."""
from types import SimpleNamespace

from axes.handlers.proxy import AxesProxyHandler
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.domain.errors import Locked, RuleViolation, Unauthenticated

from ..domain.entities import UserAccount
from ..domain.ports import Authenticator, PasswordPolicy, TokenIssuer, TokenPair
from .models import User
from .repositories import UserMapper


class DjangoPasswordPolicy(PasswordPolicy):
    def validate(self, password: str, account: UserAccount | None = None) -> None:
        user = None
        if account is not None:
            user = SimpleNamespace(
                username=account.email, first_name=account.name, last_name="",
                email=account.email,
            )
        try:
            validate_password(password, user)
        except DjangoValidationError as error:
            messages = list(error.messages)
            raise RuleViolation(messages[0], errors={"password": messages})


class DjangoAuthenticator(Authenticator):
    """Needs the request: django-axes counts wrong tries per address and email."""

    def __init__(self, request, mapper: UserMapper | None = None):
        self._request = request
        self._mapper = mapper or UserMapper()

    def authenticate(self, email: str, password: str) -> UserAccount:
        # django-axes blocks the sign-in silently; say so instead of "wrong password".
        if AxesProxyHandler.is_locked(self._request, {"email": email}):
            raise Locked("Too many wrong attempts. Please try again in 15 minutes.")
        user = authenticate(
            request=self._request, email=email.strip().lower(), password=password
        )
        if user is None or not user.is_active:
            raise Unauthenticated(
                "Wrong email or password, or this account is deactivated.",
                code="no_active_account",
            )
        return self._mapper.to_entity(user)


class JwtTokenIssuer(TokenIssuer):
    def issue(self, account: UserAccount) -> TokenPair:
        refresh = RefreshToken.for_user(User.objects.get(pk=account.id))
        return TokenPair(access=str(refresh.access_token), refresh=str(refresh))

    def refresh(self, refresh_token: str) -> TokenPair:
        serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, ValidationError):
            raise Unauthenticated("Token is invalid or expired.", code="token_not_valid")
        data = serializer.validated_data
        return TokenPair(access=data["access"], refresh=data.get("refresh", refresh_token))
