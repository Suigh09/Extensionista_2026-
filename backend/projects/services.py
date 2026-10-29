from accounts.models import AuditEvent
from django.db import IntegrityError, models, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from .models import (
    CollaborationApplication,
    CollaborationOpportunity,
    FollowUp,
    GroupInvitation,
    GroupMember,
    Project,
    ProjectGroup,
    ProjectMilestone,
    ProjectTheme,
)


def audit(actor, action, instance, fields):
    AuditEvent.objects.create(
        actor=actor,
        action=action,
        object_type=instance._meta.label,
        object_id=str(instance.pk),
        changed_fields=sorted(fields),
    )


def require_student(user):
    profile = getattr(user, "student_profile", None)
    if not profile or not user.is_active:
        raise PermissionDenied("Ação disponível somente para aluno ativo.")
    return profile


def require_member(user, group):
    student = require_student(user)
    if not GroupMember.objects.filter(group=group, student=student, is_active=True).exists():
        raise PermissionDenied("Você não participa deste grupo.")
    return student


def can_access_project(user, project):
    if not user.is_active:
        return False
    if user.role in {"ADMIN", "SECRETARIAT"}:
        return True
    if user.role == "STUDENT":
        return GroupMember.objects.filter(
            group__project=project, group__is_active=True, student__user=user, is_active=True
        ).exists()
    if user.role == "PROFESSOR":
        profile = getattr(user, "professor_profile", None)
        return bool(
            profile
            and project.groups.filter(
                models.Q(responsible_professor=profile) | models.Q(evaluator=profile),
                is_active=True,
            ).exists()
        )
    return False


def accessible_project(user, project_id):
    try:
        project = Project.objects.get(pk=project_id, is_active=True)
    except Project.DoesNotExist as error:
        raise PermissionDenied("Projeto indisponível.") from error
    if not can_access_project(user, project):
        raise NotFound("Projeto não encontrado.")
    return project


def require_approved_project(project):
    if project.status != Project.Status.APPROVED:
        raise ValidationError("O projeto precisa estar aprovado para usar esta funcionalidade.")
    return project


CURRENT_PROJECT_STATUSES = {
    Project.Status.DRAFT,
    Project.Status.PENDING_APPROVAL,
    Project.Status.CHANGES_REQUESTED,
    Project.Status.APPROVED,
    Project.Status.PAUSED,
}


def current_membership(student, excluding_project=None):
    queryset = GroupMember.objects.select_for_update().select_related("group__project").filter(
        student=student,
        is_active=True,
        group__is_active=True,
        group__project__is_active=True,
        group__project__status__in=CURRENT_PROJECT_STATUSES,
    )
    if excluding_project:
        queryset = queryset.exclude(group__project=excluding_project)
    return queryset.first()


def leave_current_project(*, actor, student, target_project, confirmed):
    membership = current_membership(student, excluding_project=target_project)
    if not membership:
        return None
    old_project = membership.group.project
    if membership:
        raise ValidationError(
            {
                "detail": (
                    f"Você já participa do projeto vigente {old_project.name}. "
                    "Solicite o cancelamento e aguarde a decisão da Secretaria."
                ),
                "code": "ACTIVE_PROJECT_CONFLICT",
                "current_project": old_project.name,
                "target_project": target_project.name if target_project else "novo projeto",
            }
        )


@transaction.atomic
def create_invitation(*, actor, group, invitee):
    from .lifecycle import require_mutable
    project = Project.objects.select_for_update().get(pk=group.project_id)
    require_mutable(project)
    locked_group = ProjectGroup.objects.select_for_update().get(pk=group.pk)
    inviter = require_member(actor, locked_group)
    # Qualquer membro ativo do grupo pode criar convites
    if not locked_group.is_active or not locked_group.project.is_active:
        raise ValidationError("O grupo não está ativo.")
    if invitee.user_id == actor.pk:
        raise ValidationError("Você já participa do grupo.")
    if (
        not invitee.user.is_active
        or not inviter.course_id
        or invitee.course_id != inviter.course_id
    ):
        raise ValidationError("Aluno não elegível para este grupo.")
    inviter_room = inviter.room_memberships.filter(is_active=True, room__status="ACTIVE").first()
    invitee_room = invitee.room_memberships.filter(is_active=True, room__status="ACTIVE").first()
    if not inviter_room or not invitee_room or inviter_room.room_id != invitee_room.room_id:
        raise ValidationError("O grupo só pode incluir alunos da mesma sala ativa.")
    if GroupMember.objects.filter(group=locked_group, student=invitee, is_active=True).exists():
        raise ValidationError("Aluno já participa do grupo.")
    occupied_slots = locked_group.members.filter(is_active=True).count() + (
        locked_group.invitations.filter(status=GroupInvitation.Status.PENDING).count()
    )
    if occupied_slots >= 4:
        raise ValidationError(
            "O grupo já possui quatro integrantes ou convites pendentes para todas as vagas."
        )
    try:
        invitation = GroupInvitation.objects.create(
            group=locked_group, invitee=invitee, invited_by=inviter
        )
    except IntegrityError as error:
        raise ValidationError("Já existe convite pendente para este aluno.") from error
    audit(actor, "INVITE", invitation, ["group", "invitee", "status"])
    from accounts.models import Notification
    from accounts.notifications import notify

    notify(
        invitee.user,
        Notification.Kind.GROUP_INVITATION,
        f"Convite para {project.name}",
        f"{actor.get_full_name()} convidou você para o grupo.",
        project=project,
    )
    return invitation


@transaction.atomic
def decide_invitation(*, actor, invitation, decision, replace_active=False):
    from .lifecycle import require_mutable, reserve_student
    project = Project.objects.select_for_update().get(pk=invitation.group.project_id)
    if decision == GroupInvitation.Status.ACCEPTED:
        require_mutable(project)
    locked = (
        GroupInvitation.objects.select_for_update()
        .select_related("group__project", "invitee__user", "invited_by")
        .get(pk=invitation.pk)
    )
    if locked.status != GroupInvitation.Status.PENDING:
        raise ValidationError("Este convite não está mais pendente.")
    student = require_student(actor)
    student = student.__class__.objects.select_for_update().get(pk=student.pk)
    if decision in {GroupInvitation.Status.ACCEPTED, GroupInvitation.Status.DECLINED}:
        if locked.invitee_id != student.pk:
            raise PermissionDenied("Somente o aluno convidado pode decidir.")
    elif decision == GroupInvitation.Status.CANCELLED:
        require_member(actor, locked.group)
    else:
        raise ValidationError("Decisão inválida.")
    if decision == GroupInvitation.Status.ACCEPTED:
        group = ProjectGroup.objects.select_for_update().get(pk=locked.group_id)
        inviter_room = locked.invited_by.room_memberships.filter(
            is_active=True, room__status="ACTIVE"
        ).first()
        invitee_room = student.room_memberships.filter(
            is_active=True, room__status="ACTIVE"
        ).first()
        if not inviter_room or not invitee_room or inviter_room.room_id != invitee_room.room_id:
            raise ValidationError("O grupo só pode incluir alunos da mesma sala ativa.")
        leave_current_project(
            actor=actor,
            student=student,
            target_project=group.project,
            confirmed=replace_active,
        )
        if student.course_id != locked.invited_by.course_id or not student.user.is_active:
            raise ValidationError("Aluno não elegível para este grupo.")
        if group.members.filter(is_active=True).count() >= 4:
            raise ValidationError("O grupo já possui quatro integrantes.")
        if GroupMember.objects.filter(group=group, student=student).exists():
            raise ValidationError("Aluno já participa do grupo.")
        reserve_student(student, group)
        GroupMember.objects.create(group=group, student=student)
    locked.status = decision
    locked.decided_at = timezone.now()
    locked.save(update_fields=["status", "decided_at"])
    audit(actor, decision, locked, ["status", "decided_at"])
    return locked


def _require_formed_group(group):
    require_approved_project(group.project)
    if not group.is_active or not group.project.is_active:
        raise ValidationError("O grupo não está ativo.")
    if group.members.filter(is_active=True).count() < 2:
        raise ValidationError("Forme o grupo com ao menos dois integrantes antes de colaborar.")


@transaction.atomic
def create_collaboration_opportunity(*, actor, group, title, description, desired_skills):
    if group is not None:
        locked_group = (
            ProjectGroup.objects.select_for_update().select_related("project").get(pk=group.pk)
        )
        require_approved_project(locked_group.project)
        creator = require_member(actor, locked_group)
        _require_formed_group(locked_group)
        if locked_group.project.groups.filter(is_active=True).count() >= 2:
            raise ValidationError("Este projeto já possui dois grupos.")
    else:
        # Oportunidade individual (sem grupo atribuído) — qualquer aluno ativo pode criar
        creator = require_student(actor)
        locked_group = None
    try:
        opportunity = CollaborationOpportunity.objects.create(
            group=locked_group,
            title=title,
            description=description,
            desired_skills=desired_skills,
            created_by=creator,
        )
    except IntegrityError as error:
        raise ValidationError("Este grupo já possui uma oportunidade aberta.") from error
    audit(
        actor,
        "CREATE_COLLABORATION_OPPORTUNITY",
        opportunity,
        ["group", "title", "description", "desired_skills", "status"],
    )
    return opportunity


@transaction.atomic
def create_collaboration_application(*, actor, opportunity, candidate_group, message):
    locked = (
        CollaborationOpportunity.objects.select_for_update()
        .select_related("group__project")
        .get(pk=opportunity.pk)
    )
    candidate = (
        ProjectGroup.objects.select_for_update()
        .select_related("project")
        .get(pk=candidate_group.pk)
    )
    creator = require_member(actor, candidate)
    _require_formed_group(candidate)
    if locked.status != CollaborationOpportunity.Status.OPEN:
        raise ValidationError("Esta oportunidade não está aberta.")
    if candidate.project_id == locked.group.project_id and locked.group is not None:
        raise ValidationError("O próprio projeto não pode se candidatar.")
    if candidate.project.groups.filter(is_active=True).count() != 1:
        raise ValidationError("Somente projetos com um grupo podem se candidatar.")
    if locked.group is not None and locked.group.project.groups.filter(is_active=True).count() >= 2:
        raise ValidationError("O projeto anunciante já possui dois grupos.")
    if locked.group is not None:
        publisher_members = set(
            locked.group.members.filter(is_active=True).values_list("student_id", flat=True)
        )
        if candidate.members.filter(is_active=True, student_id__in=publisher_members).exists():
            raise ValidationError("Os grupos da parceria não podem compartilhar integrantes.")
    try:
        application = CollaborationApplication.objects.create(
            opportunity=locked, candidate_group=candidate, message=message, created_by=creator
        )
    except IntegrityError as error:
        raise ValidationError("Este grupo já possui candidatura pendente.") from error
    audit(
        actor,
        "APPLY_COLLABORATION",
        application,
        ["opportunity", "candidate_group", "message", "status"],
    )
    return application


@transaction.atomic
def decide_collaboration_application(*, actor, application, decision):
    locked = (
        CollaborationApplication.objects.select_for_update()
        .select_related("opportunity__group__project", "candidate_group__project")
        .get(pk=application.pk)
    )
    opportunity = CollaborationOpportunity.objects.select_for_update().get(pk=locked.opportunity_id)
    if locked.status != CollaborationApplication.Status.PENDING:
        raise ValidationError("Esta candidatura não está mais pendente.")
    if decision == CollaborationApplication.Status.CANCELLED:
        require_member(actor, locked.candidate_group)
    elif decision in {
        CollaborationApplication.Status.ACCEPTED,
        CollaborationApplication.Status.DECLINED,
    }:
        require_member(actor, locked.opportunity.group)
    else:
        raise ValidationError("Decisão inválida.")
    if decision == CollaborationApplication.Status.ACCEPTED:
        if opportunity.status != CollaborationOpportunity.Status.OPEN:
            raise ValidationError("Esta oportunidade não está aberta.")
        target_project = Project.objects.select_for_update().get(
            pk=locked.opportunity.group.project_id
        )
        source_project = Project.objects.select_for_update().get(
            pk=locked.candidate_group.project_id
        )
        target_group = ProjectGroup.objects.select_for_update().get(pk=locked.opportunity.group_id)
        candidate_group = ProjectGroup.objects.select_for_update().get(pk=locked.candidate_group_id)
        _require_formed_group(target_group)
        _require_formed_group(candidate_group)
        if target_project.groups.filter(is_active=True).count() >= 2:
            raise ValidationError("O projeto anunciante já possui dois grupos.")
        if source_project.groups.filter(is_active=True).count() != 1:
            raise ValidationError("A composição do grupo candidato foi alterada.")
        candidate_group.project = target_project
        candidate_group.save(update_fields=["project", "updated_at"])
        FollowUp.objects.filter(project=source_project).update(project=target_project)
        for assignment in ProjectMilestone.objects.select_for_update().filter(
            project=source_project
        ):
            if ProjectMilestone.objects.filter(
                project=target_project, milestone=assignment.milestone
            ).exists():
                assignment.delete()
            else:
                assignment.project = target_project
                assignment.save(update_fields=["project"])
        source_project.is_active = False
        source_project.save(update_fields=["is_active", "updated_at"])

        # Tema automático de colaboração interdisciplinar (não selecionável pelo aluno)
        origin_theme = target_project.theme
        if origin_theme:
            collab_theme, _ = ProjectTheme.objects.get_or_create(
                room=origin_theme.room,
                title=f"Colaboração Interdisciplinar - {origin_theme.title}",
                defaults={
                    "description": (
                        f"Tema gerado automaticamente para colaboração interdisciplinar "
                        f"com base no tema '{origin_theme.title}'."
                    ),
                    "is_open": True,
                    "is_template": False,
                    "interdisciplinary": True,
                },
            )
            target_project.theme = collab_theme
            target_project.save(update_fields=["theme", "updated_at"])

        opportunity.status = CollaborationOpportunity.Status.MATCHED
        opportunity.save(update_fields=["status", "updated_at"])
        CollaborationApplication.objects.filter(
            opportunity=opportunity, status=CollaborationApplication.Status.PENDING
        ).exclude(pk=locked.pk).update(
            status=CollaborationApplication.Status.DECLINED, decided_at=timezone.now()
        )
        CollaborationOpportunity.objects.filter(
            group=candidate_group, status=CollaborationOpportunity.Status.OPEN
        ).update(status=CollaborationOpportunity.Status.CLOSED, updated_at=timezone.now())
    locked.status = decision
    locked.decided_at = timezone.now()
    locked.save(update_fields=["status", "decided_at"])
    audit(actor, f"COLLABORATION_{decision}", locked, ["status", "decided_at"])
    return locked
