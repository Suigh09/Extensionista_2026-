from django.db import connections
from django.db.utils import OperationalError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            connections["default"].cursor().execute("SELECT 1")
        except OperationalError:
            return Response({"status": "degraded", "service": "api"}, status=503)
        return Response({"status": "ok", "service": "api", "version": "0.1.0"})
