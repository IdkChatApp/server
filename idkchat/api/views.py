from hashlib import sha256
from time import time
from typing import Optional

from django.conf import settings
from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from simplesrp.ng_values import NG
from simplesrp.server.srp import Verifier

from .models import User, Session, PendingAuth, Dialog, Message
from .serializers import RegisterSerializer, LoginStartSerializer, LoginSerializer, DialogSerializer, MessageSerializer, \
    MessageCreateSerializer, DialogCreateSerializer
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


class LogoutView(APIView):
    def post(self, request: Request, format=None) -> Response:
        request.auth.delete()
        return Response(status=204)


class DialogsView(APIView):
    def get(self, request: Request, format=None) -> Response:
        user = request.user
        dialogs: list[Dialog] = Dialog.objects.filter(Q(user_1__id=user.id) | Q(user_2__id=user.id))
        dialogs_json = [DialogSerializer(dialog, context={"current_user": user}).data for dialog in dialogs]
        return Response(dialogs_json)

    def post(self, request: Request, format=None) -> Response:
        serializer = DialogCreateSerializer(data=request.data)
        if not serializer.is_valid():

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        if (other_user := User.objects.filter(login=serializer.data["username"]).first()) is None:
            return Response(
                {"login": ["User with login does not exist."]},
                status=status.HTTP_404_NOT_FOUND
            )

        dialog = Dialog.objects.create(user_1=request.user, user_2=other_user)
        return Response(DialogSerializer(dialog, context={"current_user": request.user}).data)


class MessagesView(APIView):
    def get(self, request: Request, dialog_id: int, format=None) -> Response:
        user = request.user
        dialog: Optional[Dialog] = Dialog.objects.filter((Q(user_1__id=user.id) | Q(user_2__id=user.id)) & Q(id=dialog_id))
        if dialog is None:
            return Response(
                {"dialog": ["This dialog does not exist."]},
                status=status.HTTP_404_NOT_FOUND
            )

        messages: list[Message] = Message.objects.filter(dialog__id=dialog.id)
        messages_json = [MessageSerializer(message, context={"current_user": user}).data for message in messages]
        return Response(messages_json)

    def post(self, request: Request, dialog_id: int, format=None) -> Response:
        user = request.user
        dialog: Optional[Dialog] = Dialog.objects.filter((Q(user_1__id=user.id) | Q(user_2__id=user.id)) & Q(id=dialog_id))
        if dialog is None:
            return Response(
                {"dialog": ["This dialog does not exist."]},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = MessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(dialog=dialog, author=request.user, text=serializer.data["text"])
        return Response(MessageSerializer(message, context={"current_user": request.user}).data)
