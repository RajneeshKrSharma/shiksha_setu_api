from django.urls import path

from .views import (
    CapabilityListView,
    ChangePasswordView,
    GrantDetailView,
    GrantListCreateView,
    LoginView,
    MeView,
    RefreshView,
    VicePrincipalDetailView,
    VicePrincipalView,
)

urlpatterns = [
    path("login/", LoginView.as_view()),
    path("refresh/", RefreshView.as_view()),
    path("me/", MeView.as_view()),
    path("change-password/", ChangePasswordView.as_view()),
    path("capabilities/", CapabilityListView.as_view()),
    path("grants/", GrantListCreateView.as_view()),
    path("grants/<uuid:grant_id>/", GrantDetailView.as_view()),
    path("vice-principal/", VicePrincipalView.as_view()),
    path("vice-principal/<uuid:vice_principal_id>/", VicePrincipalDetailView.as_view()),
]
