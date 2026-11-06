"""Transactional showcase and publication commands (Sprint 7)."""

from datetime import timedelta

from accounts.models import Notification
from accounts.notifications import institutional_staff, notify
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import (
    GroupMember,
    ProjectGroup,
    Publication,
    PublicationDocument,
    ShowcaseEntry,
    ShowcaseMemberAttendance,
)
from .services import accessible_project, audit, require_approved_project


def require_showcase_staff(user):
    if not user.is_active or user.role != "ADMIN":
        raise PermissionDenied("Ação disponível somente para o Administrador.")
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
    """UC-018: Administrador agenda a Mostra (PENDING -> SCHEDULED)."""
    require_showcase_staff(actor)
    locked_group = (
        ProjectGroup.objects.select_for_update().select_related("project").get(pk=group.pk)
    )
    if ShowcaseEntry.objects.filter(group=locked_group).exists():
        raise ValidationError("Este grupo já possui uma entrada na Mostra.")
    project = locked_group.project
    require_approved_project(project)
    if locked_group.evaluator_id:
        from academic.models import ProfessorProfile

        from .evaluation import evaluator_conflicts

        professor = (
            ProfessorProfile.objects.select_for_update(of=("self",))
            .select_related("user")
            .get(pk=locked_group.evaluator_id)
        )
        if not professor.user.is_active or professor.user.role != "PROFESSOR":
            raise ValidationError("O avaliador está inativo. Escolha outro antes de agendar.")
        if evaluator_conflicts(professor.pk, locked_group.pk, date, date + timedelta(minutes=30)):
            raise ValidationError("O avaliador já possui outra apresentação neste horário.")
    entry = ShowcaseEntry.objects.create(
        group=locked_group,
        date=date,
        end_date=date + timedelta(minutes=30),
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
    group = ProjectGroup.objects.select_for_update().get(pk=entry.group_id)
    require_evaluator(actor, group)
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
def record_member_attendance(*, actor, entry, member_attendances):
    """Confirma a lista completa uma vez; reenvio idêntico não duplica registros."""
    group = ProjectGroup.objects.select_for_update().get(pk=entry.group_id)
    require_evaluator(actor, group)
    locked = ShowcaseEntry.objects.select_for_update().get(pk=entry.pk)
    if not group.is_active:
        raise ValidationError("O grupo não está ativo.")
    from .lifecycle import require_mutable

    require_mutable(group.project)
    supplied = {}
    for item in member_attendances:
        member_id = item["member_id"]
        if member_id in supplied or not isinstance(item.get("present"), bool):
            raise ValidationError("Integrantes duplicados ou presença inválida.")
        supplied[member_id] = item["present"]
    existing = dict(locked.member_attendances.values_list("member_id", "present"))
    if existing:
        if supplied == existing:
            return locked
        raise ValidationError("A presença já foi confirmada e não pode ser alterada.")
    if locked.status not in {
        ShowcaseEntry.Status.SCHEDULED, ShowcaseEntry.Status.PRESENTED, ShowcaseEntry.Status.ABSENT,
    }:
        raise ValidationError("Somente apresentações agendadas podem ter presença registrada.")
    if group.grade_submissions.filter(concluded=True).exists():
        raise ValidationError("Avaliação concluída: não é possível complementar a presença.")
    expected = set(
        GroupMember.objects.filter(group=group, is_active=True).values_list("pk", flat=True)
    )
    if not expected or set(supplied) != expected:
        raise ValidationError(
            "Informe todos os integrantes ativos deste grupo, sem membros externos."
        )
    status = (ShowcaseEntry.Status.PRESENTED if any(supplied.values())
              else ShowcaseEntry.Status.ABSENT)
    if locked.status != ShowcaseEntry.Status.SCHEDULED and locked.status != status:
        raise ValidationError("O detalhamento deve manter a presença geral já registrada.")
    ShowcaseMemberAttendance.objects.bulk_create([
        ShowcaseMemberAttendance(entry=locked, member_id=key, present=value, recorded_by=actor)
        for key, value in supplied.items()
    ])
    locked.status = status
    locked.save(update_fields=["status", "updated_at"])
    audit(actor, "RECORD_MEMBER_ATTENDANCE", locked, ["member_attendances"])
    _notify_group_members(
        actor, locked.group, "Presença registrada",
        "Presença dos membros foi registrada na Mostra.",
        locked.group.project,
    )
    return locked


@transaction.atomic
def cancel_showcase_entry(*, actor, entry, reason=""):
    """Administrador cancela a entrada na Mostra."""
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
    from .publication_workflow import is_leader

    project = type(project).objects.select_for_update().get(pk=project.pk)
    if not is_leader(actor, project):
        raise PermissionDenied("Somente o líder pode enviar documentos.")
    if project.publication_documents.exclude(workflow="LEGACY").exists():
        raise ValidationError(
            "Use o formulário do acervo; o fluxo atual não aceita uploads avulsos."
        )
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
    """Compatibilidade de URL, sem permitir publicação direta pelo aluno."""
    from .publication_workflow import confirm_publication

    return confirm_publication(actor=actor, project_id=project.pk, expected_document=document.pk)


@transaction.atomic
def withdraw_publication(*, actor, publication, reason=""):
    """Administrador retira a publicação (histórico preservado, sem republicação)."""
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
