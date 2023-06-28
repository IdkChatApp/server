import asyncio
from time import time
from typing import Optional

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from channels_presence.decorators import touch_presence_async, remove_presence_async
from channels_presence.models import Room
from django.conf import settings
from django.db.models import Q

from api.models import User, Session, Dialog, Message, ReadState
from api.serializers import DialogSerializer
from api.utils import JWT
from ws.utils import WS_OP, WSClose


class IdkConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user: Optional[User] = None
        self.closed = False
        self.heartbeat_task = None

    async def handle_0(self, data: dict) -> None:
        secret = getattr(settings, "JWT_KEY")
        if not (token := data.get("token")) or not (sess := JWT.decode(token, secret)):
            return await self.close(WSClose.UNAUTHORIZED)

        session = await Session.objects.filter(
            id=sess["session_id"], user__id=sess["user_id"], session_key=sess["session_key"],
            expire_timestamp__gt=int(time())
        ).afirst()
        if session is None:
            return await self.close(WSClose.UNAUTHORIZED)

        self.user = await sync_to_async(lambda: session.user)()
        await self.channel_layer.group_add(f"user_{self.user.id}", self.channel_name)
        await Room.objects.add_async("idkchat", self.channel_name, self.user)

    async def handle_2(self, data: dict) -> None:
        if "dialog_id" not in data: return await self.close(WSClose.INVALID_MESSAGE)
        dialog = await Dialog.objects.aget(
            Q(id=data["dialog_id"]) & (Q(user_1__id=self.user.id) | Q(user_2__id=self.user.id)))
        last_message = await Message.objects.filter(dialog__id=dialog.id).order_by("-id").afirst()

        read_state: ReadState = await ReadState.objects.filter(user__id=self.user.id, dialog__id=dialog.id).afirst() or \
                                await ReadState.objects.acreate(user=self.user, dialog=dialog)

        last_message_id = last_message.id if last_message else 0
        read_state.message_id = last_message_id
        await read_state.asave()

        await sync_to_async(lambda: dialog.user_1)()
        await sync_to_async(lambda: dialog.user_2)()

        unread = await Message.objects.filter(id__gt=last_message_id).acount()

        await get_channel_layer().group_send(
            f"user_{self.user.id}",
            {
                "type": "chat_event",
                "op": WS_OP.DIALOG_UPDATE,
                "data": DialogSerializer(dialog, context={"current_user": self.user, "read_state": read_state,
                                                          "last_message": last_message, "unread_count": unread}).data
            }
        )

    @touch_presence_async
    async def handle_4(self, data: dict) -> None:
        if self.heartbeat_task is not None:
            self.heartbeat_task.cancel()
        self.heartbeat_task = asyncio.get_event_loop().create_task(self.heartbeat_timeout())
        await self.send_json({"op": WS_OP.HEARTBEAT_ACK, "d": None})

    async def connect(self):
        await super().connect()
        self.heartbeat_task = asyncio.get_event_loop().create_task(self.heartbeat_timeout())
        await self.send_json({"op": WS_OP.HELLO, "d": {"heartbeat_interval": 10000}})

    @remove_presence_async
    async def disconnect(self, code):
        self.closed = True
        if self.user is not None:
            await self.channel_layer.group_discard(f"user_{self.user.id}", self.channel_name)
        if self.heartbeat_task is not None:
            self.heartbeat_task.cancel()

    async def heartbeat_timeout(self):
        await asyncio.sleep(25)
        await self.close(WSClose.TIMEOUT)

    async def receive_json(self, content: dict, **kwargs):
        if "op" not in content or not isinstance(content["op"], int) \
                or "d" not in content or not isinstance(content["d"], (dict, type(None),)):
            return await self.close(WSClose.INVALID_MESSAGE)
        op = content["op"]
        if op < 0: return await self.close(WSClose.INVALID_MESSAGE)
        if op not in (WS_OP.IDENTIFY, WS_OP.HEARTBEAT) and self.user is None:
            return await self.close(WSClose.UNAUTHORIZED)
        elif op == 0 and self.user is not None:
            return await self.close(WSClose.INVALID_MESSAGE)

        if (handle_func := getattr(self, f"handle_{op}", None)) is None:
            return await self.close(WSClose.INVALID_MESSAGE)

        try:
            await handle_func(content["d"])
        except KeyError:
            return await self.close(WSClose.INVALID_MESSAGE)
        if self.closed: return

    async def chat_event(self, event):
        await self.send_json({"op": event["op"], "d": event["data"]})

    async def user_event(self, event):
        if event["op"] == WS_OP.SESSION_TERM:
            return await self.close(WSClose.UNAUTHORIZED)
