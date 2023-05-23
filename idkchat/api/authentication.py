from django.conf import settings
from rest_framework import authentication, exceptions
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from .models import Session, User
from .utils import JWT


class IdkAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request: Request) -> tuple[User, None]:
        secret = getattr(settings, "JWT_KEY")
        print(request.META)
        if not (token := request.META.get('HTTP_AUTHORIZATION')) or (sess := JWT.decode(token, secret)) is None:
            print("??")
            raise exceptions.AuthenticationFailed('No such session')

        session = Session.objects.filter(
            id=sess["session_id"], user__id=sess["user_id"], session_key=sess["session_key"]
        ).first()
        if session is None:
            raise exceptions.AuthenticationFailed('No such session')

        return session.user, None


class IdkIsAuthenticated(BasePermission):
    def has_permission(self, request: Request, view):
        return bool(request.user)