from time import time
from typing import Optional

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.conf import settings
from django.db.models import Q

from api.models import User, Session, Dialog, Message, ReadState
from api.serializers import DialogSerializer
from api.utils import JWT
from ws.utils import WS_OP


class IdkConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user: Optional[User] = None
        self.closed = False

    async def handle_0(self, data: dict) -> None:
        secret = getattr(settings, "JWT_KEY")
        if not (token := data.get("token")) or not (sess := JWT.decode(token, secret)):
            return await self.close(4001)

        session = await Session.objects.filter(
            id=sess["session_id"], user__id=sess["user_id"], session_key=sess["session_key"],
            expire_timestamp__gt=int(time())
        ).afirst()
        if session is None:
            return await self.close(4001)

        self.user = await sync_to_async(lambda: session.user)()
        await self.channel_layer.group_add(f"user_{self.user.id}", self.channel_name)

    async def handle_2(self, data: dict) -> None:
        if "dialog_id" not in data: return await self.close(4000)
        dialog = await Dialog.objects.aget(Q(id=data["dialog_id"]) & (Q(user_1__id=self.user.id) | Q(user_2__id=self.user.id)))
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

    async def disconnect(self, code):
        self.closed = True
        if self.user is not None:
            await self.channel_layer.group_discard(f"user_{self.user.id}", self.channel_name)

    async def receive_json(self, content: dict, **kwargs):
        if "op" not in content or not isinstance(content["op"], int) \
                or "d" not in content or not isinstance(content["d"], dict):
            return await self.close(4000)
        op = content["op"]
        if op < 0: return await self.close(4000)
        if op != 0 and self.user is None: return await self.close(4001)
        elif op == 0 and self.user is not None: return await self.close(4000)

        if (handle_func := getattr(self, f"handle_{op}", None)) is None:
            return await self.close(4000)

        try:
            await handle_func(content["d"])
        except KeyError:
            return await self.close(4005)
        if self.closed: return

    async def chat_event(self, event):
        await self.send_json({"op": event["op"], "d": event["data"]})

    async def user_event(self, event):
        if event["op"] == WS_OP.SESSION_TERM:
            return await self.close(4001)
