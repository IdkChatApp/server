import asyncio
from datetime import timedelta
from time import time
from typing import Optional

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from channels_presence.decorators import touch_presence_async, remove_presence_async
from channels_presence.models import Room, Presence
from channels_presence.signals import presence_changed
from django.conf import settings
from django.db.models import Q
from django.dispatch import receiver
from django.utils.timezone import now

from api.models import User, Session, Dialog, Message, ReadState
from api.serializers import DialogSerializer
from api.utils import JWT
from ws.utils import WS_OP, WSClose

channel_layer = get_channel_layer()


class IdkConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user: Optional[User] = None
        self.closed = False
        self.heartbeat_task = None
        self.tracked_presences = set()

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

        await self.send_json({"op": WS_OP.READY, "d": None})

    async def handle_2(self, data: dict) -> None:
        if "dialog_id" not in data: return await self.close(WSClose.INVALID_MESSAGE)
        dialog = await Dialog.objects.select_related("user_1", "user_2").aget(
            Q(id=data["dialog_id"]) & (Q(user_1__id=self.user.id) | Q(user_2__id=self.user.id)))
        last_message = await Message.objects.filter(dialog__id=dialog.id).order_by("-id").afirst()

        read_state: ReadState = await ReadState.objects.filter(user__id=self.user.id, dialog__id=dialog.id).afirst() or \
                                await ReadState.objects.acreate(user=self.user, dialog=dialog)

        last_message_id = last_message.id if last_message else 0
        read_state.message_id = last_message_id
        await read_state.asave()

        unread = await Message.objects.filter(id__gt=last_message_id).acount()

        await channel_layer.group_send(
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

    async def handle_7(self, data: dict) -> None:
        subscribe_users = data.get("subscribe_users", [])[:100]
        result = {"presences_changed": [], "subscribed": []}
        for user_id in subscribe_users:
            if not isinstance(user_id, int): return await self.close(WSClose.INVALID_MESSAGE)
            if user_id in self.tracked_presences:
                continue
            if not await Dialog.objects.filter(
                    Q(user_1__id=self.user.id) & Q(user_2__id=user_id) |
                    Q(user_1__id=user_id) & Q(user_2__id=self.user.id)
            ).aexists():
                continue
            self.tracked_presences.add(user_id)
            await self.channel_layer.group_add(f"presence_{user_id}", self.channel_name)

            last_seen = now() - timedelta(seconds=15)
            online = await Presence.objects.filter(user__id=user_id, last_seen__gt=last_seen).aexists()
            result["presences_changed"].append({"user_id": user_id, "status": "online" if online else "offline"})

        result["subscribed"] = list(self.tracked_presences)
        await self.send_json({"op": WS_OP.PRESENCES, "d": result})

    async def connect(self):
        await super().connect()
        self.heartbeat_task = asyncio.get_event_loop().create_task(self.heartbeat_timeout())
        await self.send_json({"op": WS_OP.HELLO, "d": {"heartbeat_interval": 10000}})

    @remove_presence_async
    async def disconnect(self, code):
        self.closed = True
        if self.user is not None:
            await self.channel_layer.group_discard(f"user_{self.user.id}", self.channel_name)
        for user_id in self.tracked_presences:
            await self.channel_layer.group_discard(f"presence_{user_id}", self.channel_name)
        if self.heartbeat_task is not None:
            self.heartbeat_task.cancel()

    async def heartbeat_timeout(self):
        await asyncio.sleep(15)
        await self.close(WSClose.TIMEOUT)

    async def receive_json(self, content: dict, **kwargs):
        if "op" not in content or not isinstance(content["op"], int) \
                or "d" not in content or not isinstance(content["d"], (dict, type(None),)):
            return await self.close(WSClose.INVALID_MESSAGE)
        op = content["op"]
        if op < 0:
            return await self.close(WSClose.INVALID_MESSAGE)
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


@receiver(presence_changed)
def broadcast_presence(room: Room, added: Presence = None, removed: Presence = None, **kwargs):
    if room.channel_name != "idkchat": return
    if added is None and removed is None: return

    user = added.user if added is not None else removed
    if removed is not None: user.id = user.user_id

    async def _bc():
        last_seen = now() - timedelta(seconds=15)
        presence_ex = await Presence.objects.filter(user__id=user.id, last_seen__gt=last_seen).aexists()
        if removed is not None and presence_ex:
            return
        await channel_layer.group_send(f"presence_{user.id}", {
            "type": "chat_event",
            "op": WS_OP.PRESENCES,
            "data": {
                "presences_changed": [{"user_id": user.id, "status": "online" if added is not None else "offline"}]
            }
        })

    asyncio.get_event_loop().create_task(_bc())
