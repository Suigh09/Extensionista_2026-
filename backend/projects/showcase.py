"""Transactional showcase and publication commands (Sprint 7)."""

from accounts.models import Notification
from accounts.notifications import institutional_staff, notify
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import (
    ProjectGroup,
    Publication,
    PublicationDocument,
    ShowcaseEntry,
)
from .services import accessible_project, audit, require_approved_project


def require_showcase_staff(user):
    if not user.is_active or user.role not in {"ADMIN", "SECRETARIAT"}:
        raise PermissionDenied("Ação disponível somente para secretaria ou administração.")
    return user


def require_evaluator(user, group):
    if not user.is_active or user.role != "PROFESSOR":
        raise PermissionDenied("Ação disponível somente para professor.")
    profile = getattr(user, "professor_profile", None)
    if not profile or group.evaluator_id != profile.pk:
        raise PermissionDenied("Você não é o avaliador designado deste grupo.")
    return profile


def require_orientador(user, project):
    if not user.is_active or user.role != "PROFESSOR":
        raise PermissionDenied("Ação disponível somente para professor.")
    profile = getattr(user, "professor_profile", None)
    if not profile:
        raise PermissionDenied("Perfil de professor não encontrado.")
    if not project.groups.filter(
        responsible_professor=profile, is_active=True
    ).exists():
        raise PermissionDenied("Você não é o orientador deste projeto.")
    return profile


@transaction.atomic
def create_showcase_entry(*, actor, group, date, location, notes=""):
    """UC-018: Secretaria agenda a Mostra (PENDING -> SCHEDULED)."""
    require_showcase_staff(actor)
    locked_group = (
        ProjectGroup.objects.select_for_update().select_related("project").get(pk=group.pk)
    )
    if ShowcaseEntry.objects.filter(group=locked_group).exists():
        raise ValidationError("Este grupo já possui uma entrada na Mostra.")
    project = locked_group.project
    require_approved_project(project)
    entry = ShowcaseEntry.objects.create(
        group=locked_group,
        date=date,
        location=location,
        status=ShowcaseEntry.Status.SCHEDULED,
        decided_by=actor,
        notes=notes,
    )
    audit(actor, "SCHEDULE_SHOWCASE", entry, ["group", "date", "location", "status"])
    _notify_group_members(
        actor,
        locked_group,
        "Mostra agendada",
        f"Sua apresentação foi agendada para {date:%d/%m/%Y %H:%M} em {location}.",
        project,
    )
    return entry


@transaction.atomic
def record_presence(*, actor, entry, status, notes=""):
    """UC-019: Avaliador registra PRESENTED ou ABSENT."""
    require_evaluator(actor, entry.group)
    locked = ShowcaseEntry.objects.select_for_update().get(pk=entry.pk)
    if locked.status != ShowcaseEntry.Status.SCHEDULED:
        raise ValidationError("Somente apresentações agendadas podem ter presença registrada.")
    if status not in {ShowcaseEntry.Status.PRESENTED, ShowcaseEntry.Status.ABSENT}:
        raise ValidationError("Status inválido para registro de presença.")
    locked.status = status
    locked.notes = notes or locked.notes
    locked.save(update_fields=["status", "notes", "updated_at"])
    audit(actor, f"RECORD_{status}", locked, ["status", "notes"])
    _notify_group_members(
        actor,
        locked.group,
        "Resultado da Mostra",
        f"Sua apresentação foi registrada como {locked.get_status_display()}.",
        locked.group.project,
    )
    return locked


@transaction.atomic
def cancel_showcase_entry(*, actor, entry, reason=""):
    """Secretaria cancela a entrada na Mostra."""
    require_showcase_staff(actor)
    locked = ShowcaseEntry.objects.select_for_update().get(pk=entry.pk)
    if locked.status in {ShowcaseEntry.Status.PRESENTED, ShowcaseEntry.Status.ABSENT}:
        raise ValidationError(
            "Não é possível cancelar uma entrada já apresentada ou ausente."
        )
    locked.status = ShowcaseEntry.Status.CANCELLED
    locked.notes = reason or locked.notes
    locked.save(update_fields=["status", "notes", "updated_at"])
    audit(actor, "CANCEL_SHOWCASE", locked, ["status", "notes"])
    return locked


@transaction.atomic
def generate_publication_document(*, actor, project, pdf_file, consent_given=False):
    """Aluno gera o documento publicável (versionado)."""
    from .services import require_student
    require_student(actor)
    project = accessible_project(actor, project.pk)
    group = (
        project.groups.filter(is_active=True, members__student__user=actor, members__is_active=True)
        .first()
    )
    if not group:
        raise PermissionDenied("Você não participa deste grupo.")
    if PublicationDocument.objects.filter(project=project).exists():
        last = PublicationDocument.objects.filter(project=project).order_by("-version").first()
        version = (last.version or 0) + 1
    else:
        version = 1
    document = PublicationDocument.objects.create(
        project=project,
        version=version,
        pdf=pdf_file,
        original_name=pdf_file.name,
        content_type=getattr(pdf_file, "content_type", "application/pdf") or "application/pdf",
        size=getattr(pdf_file, "size", 0),
        status=PublicationDocument.Status.PENDING,
        consent_given=consent_given,
        consent_at=timezone.now() if consent_given else None,
        consent_by=actor if consent_given else None,
        generated_by=actor,
    )
    audit(
        actor,
        "GENERATE_PUBLICATION_DOCUMENT",
        document,
        ["project", "version", "status", "consent_given"],
    )
    for staff_user in institutional_staff():
        notify(
            staff_user,
            Notification.Kind.DOCUMENT_APPROVED,
            "Documento pendente de aprovação",
            f"Um documento publicável foi gerado para o projeto {project.name}.",
            project=project,
        )
    return document


@transaction.atomic
def review_publication_document(*, actor, document, status, review=""):
    """Orientador aprova ou reprova o documento."""
    require_orientador(actor, document.project)
    locked = PublicationDocument.objects.select_for_update().get(pk=document.pk)
    if locked.status != PublicationDocument.Status.PENDING:
        raise ValidationError("Somente documentos pendentes podem ser revisados.")
    if status not in {PublicationDocument.Status.APPROVED, PublicationDocument.Status.REJECTED}:
        raise ValidationError("Status de revisão inválido.")
    locked.status = status
    locked.review = review
    locked.reviewed_by = getattr(actor, "professor_profile", None)
    locked.reviewed_at = timezone.now()
    locked.save(update_fields=["status", "review", "reviewed_by", "reviewed_at"])
    audit(actor, f"REVIEW_DOCUMENT_{status}", locked, ["status", "review", "reviewed_at"])
    group = document.project.groups.filter(is_active=True).first()
    _notify_group_members(
        actor,
        group,
        f"Documento {locked.get_status_display().lower()}",
        f"O documento publicável do projeto {locked.project.name} "
        f"foi {locked.get_status_display().lower()}.",
        locked.project,
    )
    if status == PublicationDocument.Status.APPROVED:
        kind = Notification.Kind.DOCUMENT_APPROVED
    else:
        kind = Notification.Kind.DOCUMENT_REJECTED
    for staff_user in institutional_staff():
        notify(
            staff_user,
            kind,
            f"Documento {locked.get_status_display().lower()}",
            f"Documento do projeto {locked.project.name} "
            f"foi {locked.get_status_display().lower()}.",
            project=locked.project,
        )
    return locked


@transaction.atomic
def publish_project(*, actor, project, document):
    """Aluno + orientador publicam o projeto no acervo."""
    from .services import require_student
    require_student(actor)
    project = accessible_project(actor, project.pk)
    document = PublicationDocument.objects.select_for_update().get(pk=document.pk)
    if document.project_id != project.pk:
        raise ValidationError("O documento não pertence a este projeto.")
    if document.status != PublicationDocument.Status.APPROVED:
        raise ValidationError("O documento precisa estar aprovado para publicar.")
    if not document.consent_given:
        raise ValidationError("O consentimento explícito é obrigatório para publicar.")
    if Publication.objects.filter(project=project).exists():
        raise ValidationError("Este projeto já possui publicação no acervo.")
    entry = ShowcaseEntry.objects.filter(
        group__project=project, status=ShowcaseEntry.Status.PRESENTED
    ).first()
    if not entry:
        raise ValidationError(
            "O projeto precisa ter sido apresentado na Mostra para ser publicado."
        )
    publication = Publication.objects.create(
        project=project,
        document=document,
        published_at=timezone.now(),
        published_by_student=actor,
    )
    audit(actor, "PUBLISH_PROJECT", publication, ["project", "document", "published_at"])
    group = project.groups.filter(is_active=True).first()
    _notify_group_members(
        actor,
        group,
        "Publicação realizada",
        f"O projeto {project.name} foi publicado no acervo.",
        project,
    )
    for staff_user in institutional_staff():
        notify(
            staff_user,
            Notification.Kind.PUBLICATION_CREATED,
            "Nova publicação no acervo",
            f"O projeto {project.name} foi publicado no acervo.",
            project=project,
        )
    return publication


@transaction.atomic
def withdraw_publication(*, actor, publication, reason=""):
    """Secretaria retira a publicação (histórico preservado, sem republicação)."""
    require_showcase_staff(actor)
    locked = Publication.objects.select_for_update().get(pk=publication.pk)
    if locked.withdrawn_at:
        raise ValidationError("Esta publicação já foi retirada.")
    locked.withdrawn_at = timezone.now()
    locked.withdrawal_reason = reason
    locked.withdrawn_by = actor
    locked.save(
        update_fields=["withdrawn_at", "withdrawal_reason", "withdrawn_by", "updated_at"]
    )
    audit(actor, "WITHDRAW_PUBLICATION", locked, ["withdrawn_at", "withdrawal_reason"])
    group = locked.project.groups.filter(is_active=True).first()
    _notify_group_members(
        actor,
        group,
        "Publicação retirada",
        f"A publicação do projeto {locked.project.name} foi retirada do acervo.",
        locked.project,
    )
    for staff_user in institutional_staff():
        notify(
            staff_user,
            Notification.Kind.PUBLICATION_WITHDRAWN,
            "Publicação retirada do acervo",
            f"A publicação do projeto {locked.project.name} foi retirada do acervo.",
            project=locked.project,
        )
    return locked


def _notify_group_members(actor, group, title, body, project):
    if not group:
        return
    members = group.members.filter(is_active=True).select_related("student__user")
    users = [
        m.student.user
        for m in members
        if m.student and m.student.user and m.student.user.is_active
    ]
    if actor in users:
        users = [u for u in users if u.pk != actor.pk]
    if users:
        notify(users, Notification.Kind.PUBLICATION_CREATED, title, body, project=project)
