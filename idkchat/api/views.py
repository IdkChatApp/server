from hashlib import sha256
from time import time
from typing import Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels_redis.core import RedisChannelLayer
from django.conf import settings
from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from simplesrp.ng_values import NG
from simplesrp.server.srp import Verifier

from ws.utils import WS_OP
from .models import User, Session, PendingAuth, Dialog, Message, ReadState
from .serializers import RegisterSerializer, LoginStartSerializer, LoginSerializer, DialogSerializer, MessageSerializer, \
    MessageCreateSerializer, DialogCreateSerializer, UserSerializer, GetUserByNameSerializer
from .storage import S3Storage
from .utils import JWT, getImage


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

        srp = Verifier(user.login, bytes.fromhex(user.salt), int("0x" + user.verifier, 16), sha256, NG.NG_2048)
        salt, B = srp.getChallenge()

        pauth = PendingAuth.objects.create(user=user, pubB=hex(B), privB=hex(srp.b), expire_timestamp=int(time() + 10))
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

        if not (
        HAMK := srp.verifyChallenge(int("0x" + serializer.data["A"], 16), int("0x" + serializer.data["M"], 16))):
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
    class MinRateThrottle(UserRateThrottle):
        rate = "30/minute"
    class MaxRateThrottle(UserRateThrottle):
        rate = "300/day"
    throttle_classes = [MinRateThrottle, MaxRateThrottle]

    def get(self, request: Request, format=None) -> Response:
        user = request.user
        dialogs: list[Dialog] = Dialog.objects.filter(Q(user_1__id=user.id) | Q(user_2__id=user.id))
        dialogs_json = [DialogSerializer(dialog, context={"current_user": user}).data for dialog in dialogs]
        return Response(dialogs_json)

    def post(self, request: Request, format=None) -> Response:
        user = request.user
        serializer = DialogCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        if (other_user := User.objects.filter(login=serializer.data["username"]).first()) is None:
            return Response(
                {"login": ["User with login does not exist."]},
                status=status.HTTP_404_NOT_FOUND
            )

        keys: dict = serializer.data["keys"]
        this_key, other_key = None, None
        if str(user.id) in keys:
            this_key = keys[str(user.id)]
        if str(other_user.id) in keys:
            other_key = keys[str(other_user.id)]

        if not this_key or not other_key:
            return Response(
                {"keys": ["Invalid keys"]},
                status=status.HTTP_400_BAD_REQUEST
            )

        q = (Q(user_1__id=user.id) & Q(user_2__id=other_user.id)) | (Q(user_1__id=other_user.id) & Q(user_2__id=user.id))
        dialog = Dialog.objects.filter(q).first() or \
                 Dialog.objects.create(user_1=user, user_2=other_user, key_1=this_key, key_2=other_key)
        return Response(DialogSerializer(dialog, context={"current_user": user}).data)


class MessagesView(APIView):
    class MinRateThrottle(UserRateThrottle):
        rate = "5/second"
    class MaxRateThrottle(UserRateThrottle):
        rate = "20/minute"
    throttle_classes = [MinRateThrottle, MaxRateThrottle]

    def get(self, request: Request, dialog_id: int, format=None) -> Response:
        user = request.user
        dialog: Optional[Dialog] = Dialog.objects.filter(
            (Q(user_1__id=user.id) | Q(user_2__id=user.id)) & Q(id=dialog_id)).first()
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
        dialog: Optional[Dialog] = Dialog.objects.filter(
            (Q(user_1__id=user.id) | Q(user_2__id=user.id)) & Q(id=dialog_id)).first()
        if dialog is None:
            return Response(
                {"dialog": ["This dialog does not exist."]},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = MessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(dialog=dialog, author=request.user, content=serializer.data["content"])

        read_state: ReadState = ReadState.objects.filter(user__id=user.id, dialog__id=dialog.id).first() or \
                                ReadState.objects.create(user=user, dialog=dialog, message_id=message.id)
        read_state.message_id = message.id
        read_state.save()

        for u in (dialog.user_1, dialog.user_2):
            async_to_sync(get_channel_layer().group_send)(
                f"user_{u.id}",
                {
                    "type": "chat_event",
                    "op": WS_OP.CREATE_MESSAGE,
                    "data": {
                        "message": MessageSerializer(message, context={"current_user": u}).data,
                        "dialog": DialogSerializer(dialog, context={"current_user": u}).data,
                    }
                }
            )

        return Response(MessageSerializer(message, context={"current_user": request.user}).data)


class UsersMeView(APIView):
    def get(self, request: Request, format=None) -> Response:
        return Response(UserSerializer(request.user).data)

    def patch(self, request: Request, format=None) -> Response:
        user = request.user
        if request.data["avatar"] or request.data["avatar"] is None:
            avatar = request.data["avatar"]
            if avatar is not None:
                image = getImage(avatar)
                avatar = user.avatar
                if (avatar_hash := S3Storage.setAvatar(user.id, image, 512)) is not None:
                    avatar = avatar_hash

            user.avatar = avatar
            user.save()

        return Response(UserSerializer(user).data)


class GetUserByName(APIView):
    class MinRateThrottle(UserRateThrottle):
        rate = "30/minute"
    class MaxRateThrottle(UserRateThrottle):
        rate = "150/day"
    throttle_classes = [MinRateThrottle, MaxRateThrottle]

    def post(self, request: Request, format=None) -> Response:
        serializer = GetUserByNameSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        if (other_user := User.objects.filter(login=serializer.data["username"]).first()) is None:
            return Response(
                {"login": ["User with login does not exist."]},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(UserSerializer(other_user).data)
