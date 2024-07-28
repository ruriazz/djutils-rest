from django.http import HttpResponse
from rest_framework.views import APIView


class Ping(APIView):
    def dispatch(self, request, *args, **kwargs) -> HttpResponse:
        return HttpResponse('PONG!')