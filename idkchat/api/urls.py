from django.urls import path

from .views import LoginView, LoginStartView

urlpatterns = [
    path("login-start/", LoginStartView.as_view()),
    path("login/", LoginView.as_view()),
]
