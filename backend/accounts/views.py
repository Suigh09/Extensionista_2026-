import hashlib
from datetime import timedelta

from academic.models import StudentProfile
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import LoginAttempt, Notification, User, cpf_fingerprint, normalize_digits
from .permissions import IsInstitutionalAdmin
from .serializers import NotificationSerializer, ProfileSerializer, UserCreateSerializer


def identifier_digest(identifier: str) -> str:
    return hashlib.sha256(identifier.strip().casefold().encode()).hexdigest()


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


def resolve_username(identifier: str) -> str | None:
    normalized = identifier.strip().casefold()
    user = User.objects.filter(username=normalized).first()
    if user:
        return user.username
    student = (
        StudentProfile.objects.select_related("user").filter(ra=identifier.strip().upper()).first()
    )
    if student:
        return student.user.username
    digits = normalize_digits(identifier)
    if len(digits) == 11:
        student = (
            StudentProfile.objects.select_related("user")
            .filter(cpf_hash=cpf_fingerprint(digits))
            .first()
        )
        if student:
            return student.user.username
    return None


class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @method_decorator(csrf_protect)
    @transaction.atomic
    def post(self, request):
        identifier = str(request.data.get("identifier", ""))
        password = str(request.data.get("password", ""))
        now = timezone.now()
        username = resolve_username(identifier)
        # Identificadores inexistentes são limitados pelo throttle e não geram
        # registros persistentes, evitando crescimento arbitrário da tabela.
        if not username:
            authenticate(request, username="__invalid__", password=password)
            return Response(
                {"detail": "Credenciais inválidas ou acesso temporariamente indisponível."},
                status=400,
            )
        client_address = str(request.META.get("REMOTE_ADDR") or "unknown")
        digest = identifier_digest(f"{client_address}|{username}")
        attempt, _ = LoginAttempt.objects.select_for_update().get_or_create(
            identifier_hash=digest, defaults={"window_started_at": now}
        )
        if attempt.locked_until and attempt.locked_until > now:
            return Response(
                {"detail": "Credenciais inválidas ou acesso temporariamente indisponível."},
                status=400,
            )
        if now - attempt.window_started_at > timedelta(minutes=15):
            attempt.failures, attempt.window_started_at, attempt.locked_until = 0, now, None
        user = authenticate(request, username=username, password=password)
        if not user:
            attempt.failures += 1
            if attempt.failures >= 5:
                attempt.locked_until = now + timedelta(minutes=15)
            attempt.save()
            return Response(
                {"detail": "Credenciais inválidas ou acesso temporariamente indisponível."},
                status=400,
            )
        attempt.delete()
        login(request, user)
        return Response(ProfileSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(ProfileSerializer(request.user).data)


class UserListCreateView(APIView):
    permission_classes = [IsInstitutionalAdmin]

    def get(self, request):
        users = User.objects.order_by("first_name", "last_name")[:100]
        return Response(ProfileSerializer(users, many=True).data)

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(ProfileSerializer(user).data, status=status.HTTP_201_CREATED)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = (
            Notification.objects.filter(user=request.user)
            .select_related("project")
            .order_by("is_read", "-created_at", "id")[:100]
        )
        return Response(NotificationSerializer(items, many=True).data)


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        try:
            item = Notification.objects.get(pk=notification_id, user=request.user)
        except Notification.DoesNotExist as error:
            from rest_framework.exceptions import NotFound

            raise NotFound("Notificação não encontrada.") from error
        if not item.is_read:
            item.is_read = True
            item.read_at = timezone.now()
            item.save(update_fields=["is_read", "read_at"])
        return Response(NotificationSerializer(item).data)


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        now = timezone.now()
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, read_at=now
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
