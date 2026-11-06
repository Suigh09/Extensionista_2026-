"""Explainable evaluator recommendation and designation (Sprint 5.1)."""

import re
from datetime import timedelta

from academic.models import ProfessorProfile, normalize_expertise_text
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from .lifecycle import TERMINAL, is_admin, record_event, require_mutable
from .models import (
    EvaluatorAssignment,
    GradeSubmission,
    Project,
    ProjectForwarding,
    ProjectGroup,
    ShowcaseEntry,
)
from .services import audit

STOPWORDS = frozenset(
    {
        "de",
        "da",
        "do",
        "das",
        "dos",
        "e",
        "ou",
        "para",
        "com",
        "por",
        "em",
        "no",
        "na",
        "uma",
        "uno",
        "um",
        "as",
        "os",
        "ao",
        "aos",
        "se",
        "que",
    }
)


def required_keywords(forwarding):
    normalized = normalize_expertise_text(forwarding.required_competencies or "")
    words = re.split(r"[^a-z0-9]+", normalized)
    return sorted({word for word in words if len(word) >= 3 and word not in STOPWORDS})


def orientador_profile_ids(project):
    return set(
        project.groups.filter(is_active=True)
        .exclude(responsible_professor__isnull=True)
        .values_list("responsible_professor_id", flat=True)
    )


def evaluator_load(profile_id):
    return (
        ProjectGroup.objects.filter(
            is_active=True, evaluator_id=profile_id, project__is_active=True
        )
        .exclude(project__status__in=TERMINAL)
        .count()
    )


def recommend_evaluators(project):
    try:
        forwarding = project.forwarding
    except ProjectForwarding.DoesNotExist as error:
        raise ValidationError("O projeto precisa ser encaminhado antes de designar.") from error
    keywords = required_keywords(forwarding)
    excluded = orientador_profile_ids(project)
    professors = (
        ProfessorProfile.objects.filter(user__is_active=True, user__role="PROFESSOR")
        .select_related("user")
        .prefetch_related("expertise_items")
        .order_by("user__first_name", "user__last_name", "pk")
    )
    recommendations = []
    for professor in professors:
        if professor.pk in excluded:
            continue
        matched = {}
        for item in professor.expertise_items.all():
            for word in keywords:
                if word in item.normalized_text:
                    matched.setdefault(word, [])
                    if item.text not in matched[word]:
                        matched[word].append(item.text)
        recommendations.append(
            {
                "professor_profile_id": str(professor.pk),
                "name": professor.user.get_full_name() or professor.user.username,
                "matched": matched,
                "match_count": len(matched),
                "load": evaluator_load(professor.pk),
            }
        )
    recommendations.sort(
        key=lambda item: (
            item["match_count"] == 0,
            item["load"],
            item["name"].casefold(),
        )
    )
    return {"keywords": keywords, "recommendations": recommendations}


def evaluator_conflicts(professor_id, group_id, start, end):
    entries = ShowcaseEntry.objects.filter(
        group__evaluator_id=professor_id,
        status__in=["SCHEDULED", "PRESENTED", "ABSENT"],
        date__lt=end,
    ).exclude(group_id=group_id)
    return any((entry.end_date or entry.date + timedelta(minutes=30)) > start for entry in entries)


def evaluator_options(group):
    table = recommend_evaluators(group.project)
    entry = getattr(group, "showcase_entry", None)
    locked = bool(
        GradeSubmission.objects.filter(group=group).exists()
        or (entry and entry.status in {"PRESENTED", "ABSENT"})
    )
    top = table["recommendations"][0] if table["recommendations"] else None
    for item in table["recommendations"]:
        conflict = bool(
            entry
            and entry.status == "SCHEDULED"
            and evaluator_conflicts(
                item["professor_profile_id"],
                group.pk,
                entry.date,
                entry.end_date or entry.date + timedelta(minutes=30),
            )
        )
        item["available"] = not locked and not conflict
        item["unavailable_reason"] = (
            "Grupo já possui presença/notas registradas."
            if locked
            else "Já alocado em outra apresentação neste horário."
            if conflict
            else ""
        )
        item["requires_justification"] = item["match_count"] == 0 or bool(
            top and top["professor_profile_id"] != item["professor_profile_id"]
        )
    return {**table, "locked": locked}


@transaction.atomic
def designate_evaluator(
    *,
    actor,
    group,
    professor_profile_id,
    justification="",
    only_if_unassigned=False,
    expected_schedule=None,
):
    if not is_admin(actor):
        raise PermissionDenied("Somente o Administrador designa avaliadores.")
    group = (
        ProjectGroup.objects.select_for_update(of=("self",))
        .select_related("project", "responsible_professor")
        .get(pk=group.pk)
    )
    if not group.is_active:
        raise ValidationError("O grupo não está ativo.")
    if only_if_unassigned and group.evaluator_id is not None:
        return None
    project = Project.objects.select_for_update().get(pk=group.project_id)
    require_mutable(project)
    if project.status != Project.Status.APPROVED:
        raise ValidationError("O projeto precisa estar aprovado para designar avaliador.")
    if not ProjectForwarding.objects.filter(project=project).exists():
        raise ValidationError("O projeto precisa ser encaminhado antes de designar.")
    try:
        professor = (
            ProfessorProfile.objects.select_for_update(of=("self",))
            .select_related("user")
            .get(pk=professor_profile_id, user__is_active=True)
        )
    except (ProfessorProfile.DoesNotExist, ValueError, TypeError) as error:
        raise ValidationError("Professor indisponível para avaliação.") from error
    if professor.pk in orientador_profile_ids(project):
        raise PermissionDenied("O orientador não pode avaliar a própria sala.")
    entry = ShowcaseEntry.objects.filter(group=group).first()
    if expected_schedule is not None and (
        not entry
        or entry.status != "SCHEDULED"
        or (entry.day_id, entry.room_id, entry.updated_at) != expected_schedule
    ):
        raise ValidationError("A agenda mudou durante a alocação. Atualize e tente novamente.")
    if GradeSubmission.objects.filter(group=group).exists() or (
        entry and entry.status in {"PRESENTED", "ABSENT"}
    ):
        raise ValidationError("Não é possível trocar avaliador após registro de presença ou notas.")
    if (
        entry
        and entry.status == "SCHEDULED"
        and evaluator_conflicts(
            professor.pk, group.pk, entry.date, entry.end_date or entry.date + timedelta(minutes=30)
        )
    ):
        raise ValidationError("O avaliador já possui outra apresentação neste horário.")
    table = recommend_evaluators(project)["recommendations"]
    entry = next(
        (item for item in table if item["professor_profile_id"] == str(professor.pk)),
        None,
    )
    if entry is None:
        raise ValidationError("Professor indisponível para avaliação.")
    top = table[0] if table else None
    needs_reason = entry["match_count"] == 0 or (
        top is not None and top["professor_profile_id"] != str(professor.pk)
    )
    justification = str(justification or "").strip()[:2000]
    if needs_reason and not justification:
        raise ValidationError({"justification": "Justifique a designação fora da recomendação."})
    group.evaluator = professor
    group.save(update_fields=["evaluator", "updated_at"])
    assignment = EvaluatorAssignment.objects.create(
        group=group,
        evaluator=professor,
        recommended=[
            {
                "professor_profile_id": item["professor_profile_id"],
                "name": item["name"],
                "match_count": item["match_count"],
                "load": item["load"],
            }
            for item in table
        ],
        justification=justification,
        decided_by=actor,
    )
    audit(actor, "DESIGNATE_EVALUATOR", group, ["evaluator", "justification"])
    record_event(
        actor,
        project,
        "EVALUATOR_DESIGNATED",
        "",
        professor.user.get_full_name(),
        justification or "Avaliador designado pelo administrador.",
    )
    from accounts.models import Notification
    from accounts.notifications import notify

    notify(
        professor.user,
        Notification.Kind.EVALUATOR_DESIGNATED,
        f"Você foi designado avaliador de {project.name}",
        justification or "Designação do administrador.",
        project=project,
    )
    return assignment


def auto_allocate_evaluators(*, actor, day, room):
    if not is_admin(actor):
        raise PermissionDenied("Somente o Administrador aloca avaliadores.")
    entries = list(
        ShowcaseEntry.objects.filter(
            day=day,
            room=room,
            status="SCHEDULED",
            group__is_active=True,
            group__project__is_active=True,
            group__project__status="APPROVED",
        )
        .select_related("group__project", "group__evaluator")
        .order_by("date", "group__project__number", "id")
    )
    allocated, pending, preserved = [], [], []
    for entry in entries:
        group = entry.group
        if group.evaluator_id:
            preserved.append(str(group.pk))
            continue
        # No transaction spans multiple groups: a failed candidate releases its locks.
        try:
            table = evaluator_options(group)
        except ValidationError as error:
            pending.append(
                {
                    "group": str(group.pk),
                    "project_name": group.project.name,
                    "reason": str(error.detail),
                }
            )
            continue
        candidates = sorted(
            [
                item
                for item in table["recommendations"]
                if item["available"] and item["match_count"] > 0
            ],
            key=lambda item: (
                -item["match_count"],
                item["load"],
                item["name"].casefold(),
                item["professor_profile_id"],
            ),
        )
        assigned = False
        reason = (
            "Grupo já possui presença/notas registradas."
            if table["locked"]
            else "Nenhum avaliador com aderência e horário disponível. Escolha manualmente."
        )
        for candidate in candidates:
            try:
                assignment = designate_evaluator(
                    actor=actor,
                    group=group,
                    professor_profile_id=candidate["professor_profile_id"],
                    justification=(
                        "Alocação automática por aderência, disponibilidade e menor carga."
                    ),
                    only_if_unassigned=True,
                    expected_schedule=(entry.day_id, entry.room_id, entry.updated_at),
                )
            except (ValidationError, PermissionDenied) as error:
                reason = str(error.detail)
                continue
            if assignment is None:
                preserved.append(str(group.pk))
            else:
                allocated.append({"group": str(group.pk), "name": candidate["name"]})
            assigned = True
            break
        if not assigned:
            pending.append(
                {"group": str(group.pk), "project_name": group.project.name, "reason": reason}
            )
    return {"allocated": allocated, "preserved": preserved, "pending": pending}
