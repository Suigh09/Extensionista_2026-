from django.urls import path

from .views import (
    CsrfView,
    LoginView,
    LogoutView,
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
    SessionView,
    UserBulkImportView,
    UserListCreateView,
)

urlpatterns = [
    path("csrf/", CsrfView.as_view(), name="csrf"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("session/", SessionView.as_view(), name="session"),
    path("users/", UserListCreateView.as_view(), name="users"),
    path("users/import-csv/", UserBulkImportView.as_view(), name="users-import-csv"),
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/read-all/",
        NotificationReadAllView.as_view(),
        name="notifications-read-all",
    ),
    path(
        "notifications/<uuid:notification_id>/read/",
        NotificationReadView.as_view(),
        name="notifications-read",
    ),
]
