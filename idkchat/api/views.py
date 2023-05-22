from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class LoginStartView(APIView):
    def post(self, request: Request, format=None) -> Response:
        ... # TODO: start login
        return Response({})


class LoginView(APIView):
    def post(self, request: Request, format=None) -> Response:
        ... # TODO: complete login
        return Response({})