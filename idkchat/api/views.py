from hashlib import sha256
from time import time

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from simplesrp.ng_values import NG
from simplesrp.server.srp import Verifier

from .authentication import IdkIsAuthenticated
from .models import User, Session, PendingAuth
from .serializers import RegisterSerializer, LoginStartSerializer, LoginSerializer
from .utils import JWT


class LoginStartView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, format=None) -> Response:
        serializer = LoginStartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        if (user := User.objects.filter(login=serializer.data["login"]).first()) is None:
            return Response(
                {"non_field_errors": ["Invalid login or password."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        srp = Verifier(user.login, bytes.fromhex(user.salt), int("0x"+user.verifier, 16), sha256, NG.NG_2048)
        salt, B = srp.getChallenge()

        pauth = PendingAuth.objects.create(user=user, pubB=hex(B), privB=hex(srp.b), expire_timestamp=int(time()+10))
        secret = getattr(settings, "JWT_KEY")
        ticket = JWT.encode({
            "user_id": user.id,
            "auth_id": pauth.id,
            "B": B,
        }, secret, time() + 10)

        return Response({"ticket": ticket, "salt": salt.hex(), "B": hex(B)})


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, format=None) -> Response:
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        secret = getattr(settings, "JWT_KEY")

        if not (ticket := JWT.decode(serializer.data["ticket"], secret)):
            return Response(
                {"ticket": ["Invalid or expired srp ticket! Try again later."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        if (pauth := PendingAuth.objects.filter(id=ticket["auth_id"]).first()) is None:
            return Response(
                {"non_field_errors": ["Invalid or expired srp ticket! Try again later."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        user: User = pauth.user

        srp = Verifier(user.login, bytes.fromhex(user.salt), int("0x" + user.verifier, 16), sha256, NG.NG_2048)
        srp.b = int(pauth.privB, 16)
        srp.B = int(pauth.pubB, 16)
        pauth.delete()

        if not (HAMK := srp.verifyChallenge(int("0x" + serializer.data["A"], 16), int("0x" + serializer.data["M"], 16))):
            return Response(
                {"non_field_errors": ["Invalid login or password."]},
                status=status.HTTP_400_BAD_REQUEST
            )
        HAMK = int.from_bytes(HAMK, "big")

        session = Session.objects.create(user=user)
        return Response({"token": session.toJWT(), "privKey": user.privKey, "H_AMK": hex(HAMK)})


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, format=None) -> Response:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        user = User.objects.get(login=serializer.data["login"])
        session = Session.objects.create(user=user)
        return Response({"token": session.toJWT()})

