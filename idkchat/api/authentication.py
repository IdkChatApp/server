from django.conf import settings
from rest_framework import authentication, exceptions

from .models import Session
from .utils import JWT


class IdkAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        secret = getattr(settings, "JWT_KEY")
        if not (token := request.META.get('Authorization')) or (sess := JWT.decode(token, secret)) is None:
            return None

        if(session := Session.objects.filter(id=sess["id"], user__id=sess["user_id"]).first()) is None:
            raise exceptions.AuthenticationFailed('No such session')

        return session.user, None