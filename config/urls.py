from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/auth/", include("apps.accounts.api.urls")),
    path("api/", include("apps.school.api.urls")),
    path("api/", include("apps.students.api.urls")),
    path("api/", include("apps.teachers.api.urls")),
    path("api/", include("apps.staff.api.urls")),
    path("api/", include("apps.attendance.api.urls")),
    path("api/", include("apps.requests.api.urls")),
    path("api/", include("apps.exams.api.urls")),
    path("api/", include("apps.payments.api.urls")),
    path("api/", include("apps.analytics.api.urls")),
]
