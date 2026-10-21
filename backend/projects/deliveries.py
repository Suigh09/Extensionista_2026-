"""Transactional formal delivery and forwarding commands (Sprint 5)."""

from academic.models import ProfessorProfile
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .lifecycle import is_admin, record_event, require_mutable
from .models import FormalDelivery, Project, ProjectForwarding, ProjectGroup
from .services import audit
from .uploads import validate_upload


def active_groups(project):
    return project.groups.filter(is_active=True)


def member_group(actor, project):
    return (
        project.groups.filter(
            is_active=True, members__student__user=actor, members__is_active=True
        ).first()
    )


def orientador_profile(actor, group):
    if actor.role != "PROFESSOR":
        return None
    profile = ProfessorProfile.objects.filter(user=actor).first()
    if profile is None or group.responsible_professor_id != profile.pk:
        return None
    return profile


def latest_delivery(project, group):
    return (
        FormalDelivery.objects.filter(project=project, group=group)
        .order_by("-version")
        .first()
    )


def group_approved_delivery(project, group):
    return (
        FormalDelivery.objects.filter(
            project=project, group=group, status=FormalDelivery.Status.APPROVED
        )
        .order_by("-version")
        .first()
    )


@transaction.atomic
def submit_delivery(*, actor, project, uploaded, notes=""):
    project = Project.objects.select_for_update().get(pk=project.pk)
    require_mutable(project)
    if project.status != Project.Status.APPROVED:
        raise ValidationError("A proposta precisa estar aprovada para entregar.")
    if project.cancellation_requests.filter(status="PENDING").exists():
        raise ValidationError("Há cancelamento pendente para este projeto.")
    group = member_group(actor, project)
    if group is None:
        raise PermissionDenied("Somente integrantes do grupo podem entregar.")
    if group.responsible_professor_id is None:
        raise ValidationError("O grupo precisa de um professor orientador definido.")
    pending = latest_delivery(project, group)
    if pending is not None and pending.status == FormalDelivery.Status.SUBMITTED:
        raise ValidationError("Já existe uma entrega aguardando avaliação.")
    last_version = (
        FormalDelivery.objects.filter(project=project, group=group)
        .order_by("-version")
        .values_list("version", flat=True)
        .first()
        or 0
    )
    original_name, content_type, size = validate_upload(uploaded)
    try:
        with transaction.atomic():
            delivery = FormalDelivery.objects.create(
                project=project,
                group=group,
                version=last_version + 1,
                title_snapshot=project.name,
                about_snapshot=project.about,
                notes=notes.strip()[:2000],
                document=uploaded,
                original_name=original_name,
                content_type=content_type,
                size=size,
                status=FormalDelivery.Status.SUBMITTED,
                submitted_by=actor,
            )
    except IntegrityError as error:
        raise ValidationError("Já existe uma entrega aguardando avaliação.") from error
    record_event(
        actor,
        project,
        "DELIVERY_SUBMITTED",
        f"v{last_version}",
        f"v{delivery.version}",
        f"Entrega v{delivery.version} enviada pelo grupo.",
    )
    from accounts.models import Notification
    from accounts.notifications import notify

    if group.responsible_professor_id:
        notify(
            group.responsible_professor.user,
            Notification.Kind.DELIVERY_SUBMITTED,
            f"Entrega recebida de {project.name}",
            f"Versão {delivery.version} aguarda avaliação.",
            project=project,
        )
    return delivery


@transaction.atomic
def review_delivery(*, actor, delivery, decision, feedback=""):
    project = Project.objects.select_for_update().get(pk=delivery.project_id)
    require_mutable(project)
    delivery = FormalDelivery.objects.select_for_update().get(pk=delivery.pk)
    if delivery.status != FormalDelivery.Status.SUBMITTED:
        raise ValidationError("Esta entrega não está aguardando avaliação.")
    group = ProjectGroup.objects.select_related("responsible_professor").get(
        pk=delivery.group_id
    )
    profile = orientador_profile(actor, group)
    if profile is None:
        raise PermissionDenied("Somente o professor orientador pode avaliar a entrega.")
    feedback = str(feedback or "").strip()[:2000]
    if decision == FormalDelivery.Status.CHANGES_REQUESTED and not feedback:
        raise ValidationError({"feedback": "Informe os ajustes necessários."})
    if decision not in {
        FormalDelivery.Status.APPROVED,
        FormalDelivery.Status.CHANGES_REQUESTED,
    }:
        raise ValidationError("Decisão inválida.")
    delivery.status = decision
    delivery.review_feedback = feedback
    delivery.reviewed_by = profile
    delivery.reviewed_at = timezone.now()
    delivery.save(
        update_fields=[
            "status",
            "review_feedback",
            "reviewed_by",
            "reviewed_at",
        ]
    )
    record_event(
        actor,
        project,
        "DELIVERY_REVIEWED",
        f"v{delivery.version}",
        f"v{delivery.version}:{decision}",
        feedback or "Entrega aprovada pelo orientador.",
    )
    return delivery


@transaction.atomic
def forward_project(*, actor, project, observations="", required_competencies=""):
    project = Project.objects.select_for_update().get(pk=project.pk)
    require_mutable(project)
    if project.status != Project.Status.APPROVED:
        raise ValidationError("A proposta precisa estar aprovada para encaminhar.")
    if project.cancellation_requests.filter(status="PENDING").exists():
        raise ValidationError("Há cancelamento pendente para este projeto.")
    groups = list(active_groups(project).select_related("responsible_professor"))
    if not groups:
        raise ValidationError("O projeto não possui grupo ativo.")
    if not any(
        group.responsible_professor
        and group.responsible_professor.user_id == actor.pk
        for group in groups
    ) and not is_admin(actor):
        raise PermissionDenied("Somente o professor orientador pode encaminhar.")
    if hasattr(project, "forwarding"):
        raise ValidationError("Este projeto já foi encaminhado à secretaria.")
    snapshot = {}
    for group in groups:
        approved = group_approved_delivery(project, group)
        if approved is None:
            raise ValidationError(
                "Todos os grupos precisam de uma entrega aprovada para encaminhar."
            )
        snapshot[str(group.pk)] = {
            "delivery_id": str(approved.pk),
            "version": approved.version,
        }
    forwarding = None
    try:
        with transaction.atomic():
            forwarding = ProjectForwarding.objects.create(
                project=project,
                snapshot=snapshot,
                observations=str(observations or "").strip()[:2000],
                required_competencies=str(required_competencies or "").strip()[:2000],
                forwarded_by=actor,
            )
    except IntegrityError as error:
        raise ValidationError("Este projeto já foi encaminhado à secretaria.") from error
    audit(
        actor,
        "FORWARD_PROJECT",
        project,
        ["forwarding", "observations", "required_competencies"],
    )
    record_event(
        actor,
        project,
        "PROJECT_FORWARDED",
        project.status,
        project.status,
        "Projeto encaminhado à secretaria.",
    )
    from accounts.models import Notification
    from accounts.notifications import institutional_staff, notify

    notify(
        institutional_staff(),
        Notification.Kind.PROJECT_FORWARDED,
        f"Encaminhamento recebido de {project.name}",
        str(observations or "").strip()[:200] or "Sem observações.",
        project=project,
    )
    return forwarding
