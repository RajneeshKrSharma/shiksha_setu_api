from uuid import UUID

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.query import QueryParams
from apps.core.domain.errors import RuleViolation
from apps.core.security.throttles import AuthRateThrottle
from config.container import container

from ..domain.capabilities import APPOINT_VICE_PRINCIPAL, GRANT_PERMISSIONS
from ..domain.entities import Role
from .permissions import RequiresCapability
from .serializers import (
    AccountOut,
    AppointViceInput,
    CapabilityOut,
    ChangePasswordInput,
    CurrentUserOut,
    GrantInput,
    GrantOut,
    LoginInput,
    RefreshInput,
    TokenPairOut,
    UpdateMeInput,
    VicePrincipalPatchInput,
)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        data = LoginInput(data=request.data)
        data.is_valid(raise_exception=True)
        pair = container.login(request).call(**data.validated_data)
        return Response(TokenPairOut(pair).data)


class RefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        data = RefreshInput(data=request.data)
        data.is_valid(raise_exception=True)
        pair = container.refresh_session().call(data.validated_data["refresh"])
        return Response(TokenPairOut(pair).data)


class MeView(APIView):
    def get(self, request):
        actor = container.actor(request.user)
        return Response(CurrentUserOut(container.get_current_user().call(actor)).data)

    def patch(self, request):
        data = UpdateMeInput(data=request.data)
        data.is_valid(raise_exception=True)
        actor = container.actor(request.user)
        actor = container.update_my_name().call(actor, data.validated_data["name"])
        return Response(CurrentUserOut(container.get_current_user().call(actor)).data)


class ChangePasswordView(APIView):
    def post(self, request):
        data = ChangePasswordInput(data=request.data)
        data.is_valid(raise_exception=True)
        container.change_password().call(container.actor(request.user), **data.validated_data)
        return Response(status=204)


class CapabilityListView(APIView):
    def get(self, request):
        return Response(CapabilityOut(container.list_capabilities().call(), many=True).data)


class GrantListCreateView(APIView):
    permission_classes = [RequiresCapability.of(GRANT_PERMISSIONS)]

    def get(self, request):
        user_id = request.query_params.get("user_id")
        try:
            wanted = UUID(user_id) if user_id else None
        except ValueError:
            raise RuleViolation("user_id is not valid.", errors={"user_id": ["Not a valid id."]})
        grants = container.list_grants().call(container.actor(request.user), user_id=wanted)
        return Response(GrantOut(grants, many=True).data)

    def post(self, request):
        data = GrantInput(data=request.data)
        data.is_valid(raise_exception=True)
        grant = container.grant_permission().call(
            container.actor(request.user),
            user_id=data.validated_data["user_id"],
            capability=data.validated_data["capability"],
            reason=data.validated_data["reason"],
        )
        return Response(GrantOut(grant).data, status=201)


class GrantDetailView(APIView):
    permission_classes = [RequiresCapability.of(GRANT_PERMISSIONS)]

    def delete(self, request, grant_id):
        container.revoke_permission().call(container.actor(request.user), grant_id)
        return Response(status=204)


class VicePrincipalView(APIView):
    """Lists the Vice Principals, and appoints one (if the school has one)."""

    permission_classes = [RequiresCapability.of(APPOINT_VICE_PRINCIPAL)]

    def get(self, request):
        query = QueryParams(request)
        found = container.list_vice_principals().call(
            container.actor(request.user), query=query.text("query"), active=query.active()
        )
        return Response(AccountOut(found, many=True).data)

    def post(self, request):
        data = AppointViceInput(data=request.data)
        data.is_valid(raise_exception=True)
        account = container.create_account().call(
            container.actor(request.user), role=Role.VICE_PRINCIPAL, **data.validated_data
        )
        return Response(AccountOut(account).data, status=201)


class VicePrincipalDetailView(APIView):
    """One Vice Principal: see, change name or password, remove (inactive) or bring back."""

    permission_classes = [RequiresCapability.of(APPOINT_VICE_PRINCIPAL)]

    def get(self, request, vice_principal_id):
        account = container.get_vice_principal().call(container.actor(request.user), vice_principal_id)
        return Response(AccountOut(account).data)

    def patch(self, request, vice_principal_id):
        data = VicePrincipalPatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        account = container.update_vice_principal().call(
            container.actor(request.user), vice_principal_id, **data.validated_data
        )
        return Response(AccountOut(account).data)

    def delete(self, request, vice_principal_id):
        container.remove_vice_principal().call(container.actor(request.user), vice_principal_id)
        return Response(status=204)
