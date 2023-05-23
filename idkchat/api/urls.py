from django.urls import path

from .views import LoginView, LoginStartView, RegisterView

urlpatterns = [
    path("auth/login-start", LoginStartView.as_view()),
    path("auth/login", LoginView.as_view()),
    path("auth/register", RegisterView.as_view()),
]
