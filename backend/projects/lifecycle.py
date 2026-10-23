"""Transactional project origin and lifecycle commands."""
from academic.models import AcademicRoom, RoomMembership, StudentProfile
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import (
    ActiveGroupSlot,
    CancellationRequest,
    CollaborationApplication,
    CollaborationOpportunity,
    GroupInvitation,
    GroupMember,
    Project,
    ProjectStateEvent,
    ProjectTheme,
)
from .services import audit, current_membership

TERMINAL = {Project.Status.CANCELLED, Project.Status.COMPLETED, Project.Status.ARCHIVED}
EDITABLE = {Project.Status.DRAFT, Project.Status.CHANGES_REQUESTED}


def is_admin(user):
    return user.is_active and user.role in {"ADMIN", "SECRETARIAT"}


def require_room_manager(user, room):
    if not is_admin(user) and not (
        user.is_active
        and user.role == "PROFESSOR"
        and room.responsible_professor.user_id == user.pk
    ):
        raise PermissionDenied(
            "Somente o professor responsável ou "
            "a administração pode gerir esta sala."
        )


def require_project_manager(user, project):
    if is_admin(user):
        return
    if user.role == "STUDENT" and project.groups.filter(
        is_active=True, members__student__user=user, members__is_active=True
    ).exists():
        return
    if user.role == "PROFESSOR" and project.groups.filter(
        is_active=True, responsible_professor__user=user
    ).exists():
        return
    raise PermissionDenied("Você não pode alterar o ciclo deste projeto.")


def require_mutable(project):
    if not project.is_active or project.status in TERMINAL | {Project.Status.PAUSED}:
        raise ValidationError("Esta ação não está disponível no estado atual do projeto.")


def reserve_student(student, group):
    # Callers lock StudentProfile first; the unique PK also protects concurrent writers.
    conflict = current_membership(student)
    if conflict and conflict.group_id != group.pk:
        raise ValidationError(
            {
                "code": "ACTIVE_PROJECT_CONFLICT",
                "detail": (
                    "Aluno já possui um grupo vigente. "
                    "Solicite o cancelamento e aguarde a decisão da Secretaria."
                ),
            }
        )
    slot = ActiveGroupSlot.objects.select_related("group__project").filter(student=student).first()
    if slot and slot.group_id != group.pk:
        if slot.group.project.status not in TERMINAL and slot.group.project.is_active:
            raise ValidationError("Aluno já possui um grupo vigente.")
        slot.delete()
    ActiveGroupSlot.objects.update_or_create(student=student, defaults={"group": group})


@transaction.atomic
def create_from_theme(*, actor, theme_id, name, about, leader_id=None, student_ids=None):
    theme = (
        ProjectTheme.objects.select_for_update()
        .select_related("room__responsible_professor")
        .get(pk=theme_id)
    )
    room = AcademicRoom.objects.select_for_update().get(pk=theme.room_id)
    if room.status != "ACTIVE" or not theme.is_open:
        raise ValidationError("Este tema não está disponível para novos projetos.")
    if theme.max_projects and theme.projects.count() >= theme.max_projects:
        raise ValidationError("O limite de projetos deste tema foi atingido.")
    if actor.role == "STUDENT":
        student = StudentProfile.objects.select_for_update().get(user=actor)
    else:
        require_room_manager(actor, theme.room)
        student = StudentProfile.objects.select_for_update().filter(pk=leader_id).first()
        if not student:
            raise ValidationError({"leader": "Selecione um aluno líder da sala."})
    if not student.user.is_active or not RoomMembership.objects.filter(
        student=student, room=room, is_active=True
    ).exists():
        raise ValidationError("O aluno precisa pertencer à sala ativa deste tema.")
    if not student.class_offering_id or not student.course_id:
        raise ValidationError("O aluno precisa de curso e turma cadastrados.")
    if current_membership(student):
        raise ValidationError(
            {
                "code": "ACTIVE_PROJECT_CONFLICT",
                "detail": (
                    "Você já possui um grupo vigente. "
                    "Aguarde o cancelamento pela Secretaria antes de criar outro projeto."
                ),
            }
        )
    project = Project.objects.create(name=name, about=about, theme=theme,
        theme_snapshot={"title": theme.title, "description": theme.description},
        class_offering=student.class_offering, origin_room=room, created_by=actor)
    group = project.groups.create(class_offering=student.class_offering, leader=student,
        responsible_professor=room.responsible_professor, name="Grupo principal")
    reserve_student(student, group)
    GroupMember.objects.create(group=group, student=student)
    record_event(actor, project, "CREATE", "", project.status, "Projeto criado a partir de tema.")
    if student_ids:
        if actor.role == "STUDENT":
            raise ValidationError(
                {"student_ids": "Somente o orientador pode associar outros alunos na criação."}
            )
        if student.pk in student_ids:
            raise ValidationError(
                {"student_ids": "O líder não deve ser repetido na lista de alunos."}
            )
        if len(set(student_ids)) != len(student_ids):
            raise ValidationError({"student_ids": "Aluno repetido na lista."})
        if len(student_ids) > 3:
            raise ValidationError(
                {"student_ids": "Informe no máximo 3 alunos além do líder."}
            )
        for extra_id in student_ids:
            assign_student(actor=actor, project=project, student_id=extra_id)
    return project


@transaction.atomic
def assign_student(*, actor, project, student_id, make_leader=False):
    project = Project.objects.select_for_update().get(pk=project.pk)
    require_mutable(project)
    if project.status not in EDITABLE:
        raise ValidationError("A composição só pode ser alterada durante a preparação da proposta.")
    group = project.groups.select_for_update().filter(is_active=True).first()
    if not group or (
        not is_admin(actor) and group.responsible_professor.user_id != actor.pk
    ):
        raise PermissionDenied(
            "Somente o orientador ou a administração pode atribuir alunos."
        )
    student = (
        StudentProfile.objects.select_for_update()
        .filter(pk=student_id, user__is_active=True)
        .first()
    )
    if not student or not RoomMembership.objects.filter(
        student=student,
        room=project.origin_room,
        is_active=True,
        room__status="ACTIVE",
    ).exists():
        raise ValidationError("Selecione um aluno ativo da sala do projeto.")
    if student.course_id != group.leader.course_id:
        raise ValidationError("Os integrantes do grupo precisam pertencer ao mesmo curso.")
    member = group.members.filter(student=student, is_active=True).first()
    if not member:
        if (
            group.members.filter(is_active=True).count()
            + group.invitations.filter(status="PENDING")
            .exclude(invitee=student)
            .count()
            >= 4
        ):
            raise ValidationError("O grupo já possui quatro vagas ocupadas ou reservadas.")
        reserve_student(student, group)
        GroupMember.objects.update_or_create(
            group=group, student=student, defaults={"is_active": True}
        )
        group.invitations.filter(invitee=student, status="PENDING").update(
            status="ACCEPTED", decided_at=timezone.now()
        )
        from accounts.models import Notification
        from accounts.notifications import notify

        notify(
            student.user,
            Notification.Kind.PROJECT_MEMBER_ADDED,
            f"Você foi incluído em {project.name}",
            f"{actor.get_full_name()} incluiu você neste projeto.",
            project=project,
        )
    if make_leader:
        group.leader = student
        group.save(update_fields=["leader", "updated_at"])
    record_event(
        actor,
        project,
        "ASSIGN_STUDENT",
        project.status,
        project.status,
        "Composição ou liderança atualizada pelo responsável.",
    )
    return project


def record_event(actor, project, action, before, after, reason):
    ProjectStateEvent.objects.create(
        project=project,
        actor=actor,
        action=action,
        previous_status=before,
        new_status=after,
        reason=reason,
    )
    audit(actor, action, project, ["status", "state_events"])


def cancel_project(actor, project, reason):
    before = project.status
    project.status = Project.Status.CANCELLED
    project.previous_status = ""
    project.save(update_fields=["status", "previous_status", "updated_at"])
    ActiveGroupSlot.objects.filter(group__project=project).delete()
    GroupInvitation.objects.filter(
        group__project=project, status="PENDING"
    ).update(status="CANCELLED", decided_at=timezone.now())
    CollaborationOpportunity.objects.filter(
        group__project=project, status="OPEN"
    ).update(status="CLOSED")
    from django.db.models import Q
    CollaborationApplication.objects.filter(
        Q(candidate_group__project=project) | Q(opportunity__group__project=project),
        status="PENDING",
    ).update(status="CANCELLED", decided_at=timezone.now())
    record_event(actor, project, "CANCEL_PROJECT", before, project.status, reason)


@transaction.atomic
def transition(*, actor, project, action, reason):
    project = Project.objects.select_for_update().get(pk=project.pk)
    require_project_manager(actor, project)
    if project.status in TERMINAL or not project.is_active:
        raise ValidationError("Este projeto está encerrado e não pode ser retomado ou alterado.")
    before = project.status
    if action in {"pause", "resume"}:
        if actor.role != "STUDENT" and not is_admin(actor):
            raise PermissionDenied(
                "A pausa e a retomada são realizadas pelos alunos ou pela administração."
            )
        if action == "pause":
            if project.status == Project.Status.PAUSED:
                raise ValidationError("O projeto já está pausado.")
            project.previous_status, project.status = project.status, Project.Status.PAUSED
        else:
            if project.status != Project.Status.PAUSED or project.previous_status not in {
                "DRAFT",
                "CHANGES_REQUESTED",
                "PENDING_APPROVAL",
                "APPROVED",
            }:
                raise ValidationError("O projeto não pode ser retomado nesta situação.")
            project.status, project.previous_status = project.previous_status, ""
        project.save(update_fields=["status", "previous_status", "updated_at"])
        record_event(actor, project, action.upper(), before, project.status, reason)
    elif action == "request-cancellation":
        if project.cancellation_requests.filter(status="PENDING").exists():
            raise ValidationError("Já existe uma solicitação de cancelamento pendente.")
        CancellationRequest.objects.create(project=project, requested_by=actor, reason=reason)
        record_event(actor, project, "REQUEST_CANCELLATION", before, before, reason)
    elif action in {"cancel", "approve-cancellation", "decline-cancellation"}:
        if not is_admin(actor):
            raise PermissionDenied("Somente Secretaria/Admin pode decidir o cancelamento.")
        pending = project.cancellation_requests.select_for_update().filter(status="PENDING").first()
        if action != "cancel" and not pending:
            raise ValidationError("Não há solicitação pendente para decidir.")
        if pending:
            pending.status = "DECLINED" if action == "decline-cancellation" else "APPROVED"
            pending.decided_by, pending.decided_at, pending.decision_note = (
                actor,
                timezone.now(),
                reason,
            )
            pending.save()
        if action == "decline-cancellation":
            record_event(actor, project, "DECLINE_CANCELLATION", before, before, reason)
        else:
            cancel_project(actor, project, reason)
    else:
        raise ValidationError("Transição inválida.")
    return project
