import re
import unicodedata
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


def normalize_expertise_text(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", value).strip().casefold()


class ActiveModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Course(ActiveModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=160)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.name = self.name.strip()
        super().save(*args, **kwargs)


class Subject(ActiveModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=160)
    workload_hours = models.PositiveSmallIntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.name = self.name.strip()
        super().save(*args, **kwargs)


class ClassOffering(ActiveModel):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="offerings")
    term = models.CharField(max_length=20)
    code = models.CharField(max_length=30)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "term", "code"], name="unique_class_offering"
            )
        ]


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="student_profile"
    )
    ra = models.CharField(max_length=40, unique=True)
    cpf_hash = models.CharField(max_length=64, unique=True)
    cpf_last4 = models.CharField(max_length=4)
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.PROTECT)
    class_offering = models.ForeignKey(
        ClassOffering, null=True, blank=True, on_delete=models.PROTECT
    )


class ProfessorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="professor_profile"
    )
    registration = models.CharField(max_length=40, blank=True)
    courses = models.ManyToManyField(Course, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True)
    class_offerings = models.ManyToManyField(ClassOffering, blank=True)


class Enrollment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.PROTECT, related_name="enrollments"
    )
    class_offering = models.ForeignKey(
        ClassOffering, on_delete=models.PROTECT, related_name="enrollments"
    )
    is_active = models.BooleanField(default=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "class_offering"],
                name="unique_student_enrollment",
            )
        ]
        indexes = [models.Index(fields=["student", "is_active"])]


class AcademicRoom(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Ativa"
        CLOSED = "CLOSED", "Encerrada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    academic_identifier = models.CharField(max_length=120, blank=True)
    responsible_professor = models.ForeignKey(
        ProfessorProfile, on_delete=models.PROTECT, related_name="academic_rooms"
    )
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "id"]
        indexes = [models.Index(fields=["responsible_professor", "status"])]

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.academic_identifier = self.academic_identifier.strip()
        super().save(*args, **kwargs)


class RoomMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(AcademicRoom, on_delete=models.PROTECT, related_name="memberships")
    student = models.ForeignKey(
        StudentProfile, on_delete=models.PROTECT, related_name="room_memberships"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_room_memberships"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student"], condition=Q(is_active=True), name="unique_active_room_student"
            )
        ]
        indexes = [
            models.Index(fields=["room", "is_active"]),
            models.Index(fields=["student", "is_active"]),
        ]


class ProfessorExpertise(models.Model):
    class Kind(models.TextChoices):
        DISCIPLINE = "DISCIPLINE", "Disciplina"
        COMPETENCY = "COMPETENCY", "Competência"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    professor = models.ForeignKey(
        ProfessorProfile, on_delete=models.PROTECT, related_name="expertise_items"
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    text = models.CharField(max_length=160)
    normalized_text = models.CharField(max_length=160, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind", "normalized_text", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["professor", "kind", "normalized_text"],
                name="unique_professor_expertise",
            )
        ]
        indexes = [models.Index(fields=["professor", "kind", "normalized_text"])]

    def save(self, *args, **kwargs):
        self.text = re.sub(r"\s+", " ", self.text).strip()
        self.normalized_text = normalize_expertise_text(self.text)
        super().save(*args, **kwargs)


class RoomTransferRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        APPROVED = "APPROVED", "Aprovada"
        DECLINED = "DECLINED", "Recusada"
        INVALIDATED = "INVALIDATED", "Invalidada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.PROTECT, related_name="room_transfer_requests"
    )
    source_room = models.ForeignKey(
        AcademicRoom, on_delete=models.PROTECT, related_name="outgoing_transfer_requests"
    )
    destination_room = models.ForeignKey(
        AcademicRoom, on_delete=models.PROTECT, related_name="incoming_transfer_requests"
    )
    requesting_professor = models.ForeignKey(
        ProfessorProfile, on_delete=models.PROTECT, related_name="requested_room_transfers"
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="decided_room_transfers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["student"], condition=Q(status="PENDING"),
                name="unique_pending_room_transfer_student",
            ),
            models.CheckConstraint(
                condition=~Q(source_room=models.F("destination_room")),
                name="room_transfer_different_rooms",
            ),
        ]
        indexes = [models.Index(fields=["status", "created_at"])]
