"""Fluxo único do acervo: líder → orientador → líder (se editado) → Administrador."""

import hashlib

from accounts.models import Notification
from accounts.notifications import institutional_staff, notify
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .grading import group_grade_value
from .lifecycle import require_mutable
from .models import GroupMember, Project, Publication, PublicationDocument, ShowcaseEntry
from .services import accessible_project, audit

W = PublicationDocument.Workflow


def is_leader(actor, project):
    return (
        actor.is_active
        and actor.role == "STUDENT"
        and project.groups.filter(
            is_active=True,
            leader__user=actor,
            members__student__user=actor,
            members__is_active=True,
        ).exists()
    )


def is_advisor(actor, project):
    return (
        actor.is_active
        and actor.role == "PROFESSOR"
        and project.groups.filter(
            is_active=True,
            responsible_professor__user=actor,
        ).exists()
    )


def advisors(project):
    return list(
        {
            group.responsible_professor.user_id: group.responsible_professor.user
            for group in project.groups.filter(is_active=True).select_related(
                "responsible_professor__user"
            )
            if group.responsible_professor
        }.values()
    )


def leaders(project):
    return list(
        {
            group.leader.user_id: group.leader.user
            for group in project.groups.filter(is_active=True).select_related("leader__user")
            if group.leader
            and GroupMember.objects.filter(
                group=group, student=group.leader, is_active=True
            ).exists()
        }.values()
    )


def document_notice(project, users, body):
    notify(
        users,
        Notification.Kind.PUBLICATION_WORKFLOW,
        f"Documento do acervo: {project.name}",
        body,
        project=project,
    )


def publication_blockers(project):
    reasons = []
    if not project.is_active or project.status != Project.Status.APPROVED:
        reasons.append("O projeto precisa estar ativo e aprovado.")
    if project.cancellation_requests.filter(status="PENDING").exists():
        reasons.append("Há cancelamento pendente.")
    if not hasattr(project, "forwarding"):
        reasons.append("O projeto precisa estar encaminhado ao Administrador.")
    groups = list(project.groups.filter(is_active=True))
    if not groups:
        reasons.append("O projeto não possui grupo ativo.")
    for group in groups:
        label = group.name or "Grupo"
        delivery = group.deliveries.order_by("-version").first()
        if delivery is None or delivery.status != "APPROVED":
            reasons.append(f"{label}: a entrega vigente precisa estar aprovada.")
        entry = ShowcaseEntry.objects.filter(group=group).first()
        if entry is None or entry.status != "PRESENTED":
            reasons.append(f"{label}: precisa ter sido apresentado na Mostra.")
        member_ids = set(group.members.filter(is_active=True).values_list("id", flat=True))
        recorded = (
            set(entry.member_attendances.values_list("member_id", flat=True)) if entry else set()
        )
        if not member_ids or not member_ids.issubset(recorded):
            reasons.append(f"{label}: falta confirmar a presença individual dos integrantes.")
        value, grade = group_grade_value(group)
        if grade is None or not grade.concluded or value is None:
            reasons.append(f"{label}: falta concluir a avaliação do grupo.")
    return reasons


def result_rows(project):
    rows = []
    for group in project.groups.filter(is_active=True):
        entry = ShowcaseEntry.objects.filter(group=group).first()
        attendance = (
            dict(entry.member_attendances.values_list("member_id", "present")) if entry else {}
        )
        value, grade = group_grade_value(group)
        rows.append(
            {
                "group": str(group.pk),
                "name": group.name,
                "grade": str(value) if value is not None else None,
                "concluded": bool(grade and grade.concluded),
                "observations": grade.comment if grade else "",
                "members": [
                    {
                        "name": member.student.user.get_full_name(),
                        "ra": member.student.ra,
                        "present": attendance.get(member.pk),
                    }
                    for member in group.members.filter(is_active=True).select_related(
                        "student__user"
                    )
                ],
            }
        )
    return rows


def project_snapshot(project):
    members = GroupMember.objects.filter(
        group__project=project, group__is_active=True, is_active=True
    ).select_related("student__user", "student__course")
    unique = {
        member.student_id: {
            "name": member.student.user.get_full_name() or member.student.user.username,
            "course": member.student.course.name if member.student.course else "Não informado",
        }
        for member in members.order_by("joined_at", "id")
    }
    return {
        "project_id": str(project.pk),
        "project_name": project.name,
        "year": timezone.localdate().year,
        "members": list(unique.values()),
        "advisors": [user.get_full_name() or user.username for user in advisors(project)],
    }


def latest_document(project):
    return project.publication_documents.order_by("-version").first()


def _locked_project(actor, project_id):
    project = accessible_project(actor, project_id)
    project = Project.objects.select_for_update().get(pk=project.pk)
    require_mutable(project)
    if Publication.objects.filter(project=project).exists():
        raise ValidationError("Este projeto já possui publicação; não é permitido novo ciclo.")
    return project


def _eligible(project):
    blockers = publication_blockers(project)
    if blockers:
        raise ValidationError({"prerequisites": blockers})


def _current(project, expected_document):
    latest = latest_document(project)
    if (str(latest.pk) if latest else None) != (
        str(expected_document) if expected_document else None
    ):
        raise ValidationError("A versão mudou. Atualize a página antes de continuar.")
    return latest


def _new_version(*, actor, project, previous, title, abstract, content, workflow, consent):
    from .publication_pdf import render_publication_pdf

    title, abstract, content = title.strip(), abstract.strip(), content.strip()
    if not title or not abstract or not content:
        raise ValidationError("Preencha título, resumo e descrição do projeto.")
    if len(title) > 180 or len(abstract) > 4000 or len(content) > 40000:
        raise ValidationError("Título, resumo ou descrição excedem o limite permitido.")
    snapshot = previous.snapshot if previous and workflow == W.LEADER else project_snapshot(project)
    version = previous.version + 1 if previous else 1
    data = render_publication_pdf(
        title=title, abstract=abstract, content=content, snapshot=snapshot, version=version
    )
    document = PublicationDocument(
        project=project,
        version=version,
        title=title,
        abstract=abstract,
        content=content,
        snapshot=snapshot,
        workflow=workflow,
        parent=previous,
        generated_by=actor,
        original_name=f"projeto-{project.number}-v{version}.pdf",
        content_type="application/pdf",
        size=len(data),
        pdf_sha256=hashlib.sha256(data).hexdigest(),
        consent_given=consent,
        consent_by=actor if workflow == W.ADVISOR else previous.consent_by,
        consent_at=timezone.now() if workflow == W.ADVISOR else previous.consent_at,
    )
    if workflow == W.LEADER:
        document.reviewed_by = actor.professor_profile
        document.reviewed_at = timezone.now()
        document.review = "Texto revisado pelo orientador; aguarda validação do líder."
    document.pdf.save(document.original_name, ContentFile(data), save=False)
    try:
        document.save()
        audit(
            actor,
            "SUBMIT_ACERVO_VERSION",
            document,
            ["version", "content", "workflow", "pdf_sha256"],
        )
        document_notice(
            project,
            advisors(project) if workflow == W.ADVISOR else leaders(project),
            f"Versão {version}: "
            + (
                "aguarda revisão do orientador."
                if workflow == W.ADVISOR
                else "valide as correções do orientador."
            ),
        )
    except Exception:
        document.pdf.delete(save=False)
        raise
    return document


@transaction.atomic
def submit_document(*, actor, project_id, expected_document, title, abstract, content, consent):
    project = _locked_project(actor, project_id)
    if not is_leader(actor, project):
        raise PermissionDenied("Somente o líder ativo pode enviar o documento.")
    _eligible(project)
    previous = _current(project, expected_document)
    if previous and previous.workflow not in {W.LEGACY, W.ADVISOR}:
        raise ValidationError("Não é possível reenviar nesta etapa.")
    if not consent:
        raise ValidationError(
            "O consentimento explícito é obrigatório para encaminhar o documento."
        )
    return _new_version(
        actor=actor,
        project=project,
        previous=previous,
        title=title,
        abstract=abstract,
        content=content,
        workflow=W.ADVISOR,
        consent=True,
    )


@transaction.atomic
def decide_document(
    *, actor, project_id, expected_document, action, title="", abstract="", content=""
):
    project = _locked_project(actor, project_id)
    current = _current(project, expected_document)
    if current is None:
        raise ValidationError("Envie o documento antes de continuar.")
    if action in {"approve", "correct"}:
        if not is_advisor(actor, project):
            raise PermissionDenied("Somente o orientador pode revisar o documento.")
        if current.workflow != W.ADVISOR:
            raise ValidationError("Esta versão não aguarda revisão do orientador.")
    elif action == "accept":
        if not is_leader(actor, project):
            raise PermissionDenied("Somente o líder pode validar as correções.")
        if current.workflow != W.LEADER:
            raise ValidationError("Esta versão não aguarda validação do líder.")
    else:
        raise ValidationError("Ação inválida.")
    _eligible(project)
    if action == "correct":
        if (title.strip(), abstract.strip(), content.strip()) == (
            current.title,
            current.abstract,
            current.content,
        ):
            raise ValidationError("Nenhuma alteração: aprove a versão sem criar uma correção.")
        return _new_version(
            actor=actor,
            project=project,
            previous=current,
            title=title,
            abstract=abstract,
            content=content,
            workflow=W.LEADER,
            consent=current.consent_given,
        )
    current.workflow = W.ADMIN
    current.status = PublicationDocument.Status.APPROVED
    if action == "approve":
        current.reviewed_by = actor.professor_profile
        current.reviewed_at = timezone.now()
        current.review = "Aprovado sem alterações pelo orientador."
    else:
        current.accepted_by = actor
        current.accepted_at = timezone.now()
    current.save(
        update_fields=[
            "workflow",
            "status",
            "reviewed_by",
            "reviewed_at",
            "review",
            "accepted_by",
            "accepted_at",
        ]
    )
    audit(
        actor,
        "APPROVE_ACERVO_VERSION" if action == "approve" else "ACCEPT_ACERVO_CORRECTION",
        current,
        ["workflow", "status"],
    )
    document_notice(
        project,
        institutional_staff(),
        f"Versão {current.version} validada. Confirme a publicação no acervo.",
    )
    return current


@transaction.atomic
def confirm_publication(*, actor, project_id, expected_document):
    from .showcase import require_showcase_staff

    require_showcase_staff(actor)
    project = _locked_project(actor, project_id)
    _eligible(project)
    current = _current(project, expected_document)
    if current is None or current.workflow != W.ADMIN or current.status != "APPROVED":
        raise ValidationError("A versão vigente precisa estar validada e aguardando o Administrador.")
    if not current.consent_given or not current.reviewed_by_id:
        raise ValidationError("Falta consentimento ou aprovação do orientador.")
    if (
        current.parent_id
        and current.generated_by_id != current.consent_by_id
        and not current.accepted_at
    ):
        raise ValidationError("O líder precisa validar a correção do orientador.")
    publication = Publication.objects.create(
        project=project,
        document=current,
        published_at=timezone.now(),
        confirmed_by=actor,
        published_by_student=current.consent_by,
        published_by_professor=current.reviewed_by,
    )
    current.workflow = W.PUBLISHED
    current.save(update_fields=["workflow"])
    audit(actor, "PUBLISH_PROJECT", publication, ["document", "published_at", "confirmed_by"])
    users = [
        member.student.user
        for member in GroupMember.objects.filter(
            group__project=project, is_active=True, group__is_active=True
        ).select_related("student__user")
    ]
    document_notice(
        project, users + advisors(project), f"Versão {current.version} publicada pelo Administrador."
    )
    return publication
