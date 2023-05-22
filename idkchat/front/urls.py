from django.urls import path

from front.views import index_page, auth_page, dialogs_page, profile_page, feedback_page

urlpatterns = [
    path("", index_page),
    path("auth", auth_page),
    path("dialogs", dialogs_page),
    path("profile", profile_page),
    path("feedback", feedback_page),
]
