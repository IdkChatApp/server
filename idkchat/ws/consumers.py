from time import time
from typing import Optional

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

from api.models import User, Session
from api.utils import JWT


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
        ...

    async def disconnect(self, code):
        self.closed = True
        await self.channel_layer.group_discard(f"user_{self.user.id}", self.channel_name)

    async def receive_json(self, content: dict):
        if "op" not in content or not isinstance(content["op"], int) \
                or "d" not in content or not isinstance(content["d"], dict):
            return await self.close(4000)
        op = content["op"]
        if op != 0 and self.user is None:
            return await self.close(4001)
        elif op == 0 and self.user is not None:
            return await self.close(4000)

        if (handle_func := getattr(self, f"handle_{op}", None)) is None:
            return await self.close(4000)

        try:
            await handle_func(content["d"])
        except:
            return await self.close(4005)
        if self.closed: return

    async def chat_event(self, event):
        await self.send_json(event["data"])