from django.urls import path

from .views import LoginView, LoginStartView, RegisterView, LogoutView, DialogsView, MessagesView

urlpatterns = [
    path("auth/login-start", LoginStartView.as_view()),
    path("auth/login", LoginView.as_view()),
    path("auth/register", RegisterView.as_view()),
    path("auth/logout", LogoutView.as_view()),

    path("chat/dialogs", DialogsView.as_view()),
    path("chat/dialogs/<int:dialog_id>/messages", MessagesView.as_view()),
]
