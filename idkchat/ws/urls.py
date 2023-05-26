from django.urls import path

from ws.consumers import IdkConsumer

websocket_urlpatterns = [
    path("ws", IdkConsumer.as_asgi())
]