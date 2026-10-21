import hashlib
import hmac
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


def normalize_digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def cpf_fingerprint(value: str) -> str:
    digits = normalize_digits(value)
    if len(digits) != 11:
        raise ValueError("CPF deve conter 11 dígitos.")
    return hmac.new(settings.SECRET_KEY.encode(), digits.encode(), hashlib.sha256).hexdigest()


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Aluno"
        PROFESSOR = "PROFESSOR", "Professor"
        SECRETARIAT = "SECRETARIAT", "Secretaria"
        ADMIN = "ADMIN", "Administrador"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField("identificador de acesso", max_length=80, unique=True)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=16, choices=Role.choices)
    REQUIRED_FIELDS = ["role"]

    def save(self, *args, **kwargs):
        self.username = self.username.strip().casefold()
        self.email = self.email.strip().casefold()
        super().save(*args, **kwargs)


class LoginAttempt(models.Model):
    identifier_hash = models.CharField(max_length=64, unique=True)
    failures = models.PositiveSmallIntegerField(default=0)
    window_started_at = models.DateTimeField()
    locked_until = models.DateTimeField(null=True, blank=True)


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=40)
    object_type = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80)
    changed_fields = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Notification(models.Model):
    """Internal notice to a user; central surface arrives in Sprint 8."""

    class Kind(models.TextChoices):
        GROUP_INVITATION = "GROUP_INVITATION", "Convite de grupo"
        ROOM_INCLUDED = "ROOM_INCLUDED", "Inclusão em sala"
        ROOM_TRANSFER_REQUESTED = "ROOM_TRANSFER_REQUESTED", "Transferência solicitada"
        ROOM_TRANSFER_DECIDED = "ROOM_TRANSFER_DECIDED", "Transferência decidida"
        PROJECT_ADJUSTMENT_REQUESTED = "PROJECT_ADJUSTMENT_REQUESTED", "Ajuste solicitado"
        DELIVERY_SUBMITTED = "DELIVERY_SUBMITTED", "Entrega recebida"
        PROJECT_FORWARDED = "PROJECT_FORWARDED", "Encaminhamento recebido"
        EVALUATOR_DESIGNATED = "EVALUATOR_DESIGNATED", "Avaliador designado"
        EVALUATION_CONCLUDED = "EVALUATION_CONCLUDED", "Avaliação concluída"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    title = models.CharField(max_length=160)
    body = models.CharField(max_length=500, blank=True)
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "id"]
        indexes = [models.Index(fields=["user", "is_read", "-created_at"])]
