from accounts.models import AuditEvent
from django.db import IntegrityError, models, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from .models import (
    AcademicRoom,
    RoomMembership,
    RoomTransferRequest,
    StudentProfile,
)


def audit(actor, action, instance, fields):
    AuditEvent.objects.create(
        actor=actor,
        action=action,
        object_type=instance._meta.label,
        object_id=str(instance.pk),
        changed_fields=sorted(fields),
    )


def require_professor(user):
    profile = getattr(user, "professor_profile", None)
    if not user.is_active or user.role != "PROFESSOR" or not profile:
        raise PermissionDenied("Ação disponível somente para professor ativo.")
    return profile


def require_owned_room(user, room_id, *, lock=False):
    professor = require_professor(user)
    queryset = AcademicRoom.objects.select_related("responsible_professor__user")
    if lock:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(pk=room_id, responsible_professor=professor)
    except AcademicRoom.DoesNotExist as error:
        # Do not reveal whether another professor owns the identifier.
        raise NotFound("Sala não encontrada.") from error


@transaction.atomic
def pull_student(*, actor, room, student):
    locked_student = (
        StudentProfile.objects.select_for_update().select_related("user").get(pk=student.pk)
    )
    locked_room = AcademicRoom.objects.select_for_update().get(pk=room.pk)
    professor = require_professor(actor)
    if locked_room.responsible_professor_id != professor.pk:
        raise PermissionDenied("Sala indisponível.")
    if locked_room.status != AcademicRoom.Status.ACTIVE:
        raise ValidationError("Sala encerrada não pode receber alunos.")
    if not locked_student.user.is_active:
        raise ValidationError("Aluno inativo não pode ser incluído.")
    current = (
        RoomMembership.objects.select_for_update()
        .select_related("room__responsible_professor__user")
        .filter(student=locked_student, is_active=True)
        .first()
    )
    if current and current.room_id == locked_room.pk:
        raise ValidationError("O aluno já pertence a esta sala.")
    if current:
        if RoomTransferRequest.objects.filter(
            student=locked_student, status=RoomTransferRequest.Status.PENDING
        ).exists():
            raise ValidationError(
                "Já existe uma solicitação de transferência pendente para este aluno."
            )
        try:
            request = RoomTransferRequest.objects.create(
                student=locked_student,
                source_room=current.room,
                destination_room=locked_room,
                requesting_professor=professor,
            )
        except IntegrityError as error:
            raise ValidationError(
                "Já existe uma solicitação de transferência pendente para este aluno."
            ) from error
        audit(
            actor,
            "REQUEST_ROOM_TRANSFER",
            request,
            ["student", "source_room", "destination_room", "status"],
        )
        from accounts.models import Notification
        from accounts.notifications import institutional_staff, notify

        notify(
            locked_student.user,
            Notification.Kind.ROOM_TRANSFER_REQUESTED,
            f"Transferência para {locked_room.name}",
            "Sua transferência foi enviada à secretaria.",
        )
        notify(
            institutional_staff(),
            Notification.Kind.ROOM_TRANSFER_REQUESTED,
            f"Transferência de {locked_student.user.get_full_name()}",
            f"{current.room.name} → {locked_room.name}.",
        )
        return current, request
    try:
        membership = RoomMembership.objects.create(
            room=locked_room, student=locked_student, assigned_by=actor
        )
    except IntegrityError as error:
        raise ValidationError("O aluno já possui uma sala ativa.") from error
    audit(actor, "ADD_ROOM_STUDENT", membership, ["room", "student", "is_active"])
    from accounts.models import Notification
    from accounts.notifications import notify

    notify(
        locked_student.user,
        Notification.Kind.ROOM_INCLUDED,
        f"Você entrou em {locked_room.name}",
        f"Professor responsável: {locked_room.responsible_professor.user.get_full_name()}.",
    )
    return membership, None


@transaction.atomic
def decide_transfer(*, actor, transfer, approve, note=""):
    if not actor.is_active or actor.role not in {"SECRETARIAT", "ADMIN"}:
        raise PermissionDenied("Somente a secretaria pode decidir transferências.")
    locked = (
        RoomTransferRequest.objects.select_for_update()
        .select_related("student", "source_room", "destination_room")
        .get(pk=transfer.pk)
    )
    if locked.status != RoomTransferRequest.Status.PENDING:
        raise ValidationError("Esta solicitação não está mais pendente.")
    StudentProfile.objects.select_for_update().get(pk=locked.student_id)
    if approve:
        destination = AcademicRoom.objects.select_for_update().get(pk=locked.destination_room_id)
        if destination.status != AcademicRoom.Status.ACTIVE:
            raise ValidationError("A sala de destino foi encerrada.")
        if destination.responsible_professor_id != locked.requesting_professor_id:
            raise ValidationError(
                "A responsabilidade da sala de destino foi alterada; revise a solicitação."
            )
        current = RoomMembership.objects.select_for_update().filter(
            student_id=locked.student_id, is_active=True
        ).first()
        if not current or current.room_id != locked.source_room_id:
            raise ValidationError("A sala atual do aluno foi alterada; revise a solicitação.")
        now = timezone.now()
        current.is_active = False
        current.left_at = now
        current.save(update_fields=["is_active", "left_at"])
        RoomMembership.objects.create(
            room=destination, student_id=locked.student_id, assigned_by=actor
        )
        locked.status = RoomTransferRequest.Status.APPROVED
    else:
        locked.status = RoomTransferRequest.Status.DECLINED
    locked.decided_by = actor
    locked.decided_at = timezone.now()
    locked.decision_note = str(note or "").strip()[:500]
    locked.save(update_fields=["status", "decided_by", "decided_at", "decision_note"])
    audit(
        actor,
        "APPROVE_ROOM_TRANSFER" if approve else "DECLINE_ROOM_TRANSFER",
        locked,
        ["status", "decided_by", "decided_at", "decision_note"],
    )
    from accounts.models import Notification
    from accounts.notifications import notify

    notify(
        locked.student.user,
        Notification.Kind.ROOM_TRANSFER_DECIDED,
        f"Transferência {'aprovada' if approve else 'recusada'}",
        f"{locked.source_room.name} → {locked.destination_room.name}.",
    )
    return locked


@transaction.atomic
def close_room(*, actor, room):
    locked = AcademicRoom.objects.select_for_update().get(pk=room.pk)
    professor = require_professor(actor)
    if locked.responsible_professor_id != professor.pk:
        raise PermissionDenied("Sala indisponível.")
    if locked.status != AcademicRoom.Status.ACTIVE:
        raise ValidationError("A sala já está encerrada.")
    now = timezone.now()
    memberships = RoomMembership.objects.select_for_update().filter(room=locked, is_active=True)
    memberships.update(is_active=False, left_at=now)
    pending_transfers = list(RoomTransferRequest.objects.select_for_update().filter(
        status=RoomTransferRequest.Status.PENDING
    ).filter(
        models.Q(source_room=locked) | models.Q(destination_room=locked)
    ))
    for transfer in pending_transfers:
        side = "origem" if transfer.source_room_id == locked.pk else "destino"
        transfer.status = RoomTransferRequest.Status.INVALIDATED
        transfer.decided_by = None
        transfer.decided_at = now
        transfer.decision_note = f"Solicitação invalidada: sala de {side} encerrada."
        transfer.save(update_fields=["status", "decided_by", "decided_at", "decision_note"])
        audit(
            actor,
            "INVALIDATE_ROOM_TRANSFER",
            transfer,
            ["status", "decided_at", "decision_note"],
        )
    locked.status = AcademicRoom.Status.CLOSED
    locked.closed_at = now
    locked.save(update_fields=["status", "closed_at", "updated_at"])
    audit(actor, "CLOSE_ROOM", locked, ["status", "closed_at", "memberships"])
    return locked
