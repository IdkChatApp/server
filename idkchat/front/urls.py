from django.urls import path

from .views import index_page, auth_page, dialogs_page, profile_page, settings_page

urlpatterns = [
    path("", index_page),
    path("auth", auth_page),
    path("dialogs", dialogs_page),
    path("profile", profile_page),
    path("settings", settings_page),
]
