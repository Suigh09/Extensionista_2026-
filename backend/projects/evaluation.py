"""Explainable evaluator recommendation and designation (Sprint 5.1)."""

import re

from academic.models import ProfessorProfile, normalize_expertise_text
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from .lifecycle import TERMINAL, is_admin, record_event
from .models import EvaluatorAssignment, Project, ProjectForwarding, ProjectGroup
from .services import audit

STOPWORDS = frozenset(
    {"de", "da", "do", "das", "dos", "e", "ou", "para", "com", "por", "em", "no", "na",
     "uma", "uno", "um", "as", "os", "ao", "aos", "se", "que"}
)


def required_keywords(forwarding):
    normalized = normalize_expertise_text(forwarding.required_competencies or "")
    words = re.split(r"[^a-z0-9]+", normalized)
    return sorted({word for word in words if len(word) >= 3 and word not in STOPWORDS})


def orientador_profile_ids(project):
    return set(
        project.groups.filter(is_active=True).exclude(
            responsible_professor__isnull=True
        ).values_list("responsible_professor_id", flat=True)
    )


def evaluator_load(profile_id):
    return ProjectGroup.objects.filter(
        is_active=True, evaluator_id=profile_id, project__is_active=True
    ).exclude(project__status__in=TERMINAL).count()


def recommend_evaluators(project):
    try:
        forwarding = project.forwarding
    except ProjectForwarding.DoesNotExist as error:
        raise ValidationError(
            "O projeto precisa ser encaminhado antes de designar."
        ) from error
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
                "name": professor.user.get_full_name(),
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


@transaction.atomic
def designate_evaluator(*, actor, group, professor_profile_id, justification=""):
    if not is_admin(actor):
        raise PermissionDenied("Somente a Secretaria/Admin designa avaliadores.")
    group = ProjectGroup.objects.select_for_update(of=("self",)).select_related(
        "project", "responsible_professor"
    ).get(pk=group.pk)
    if not group.is_active:
        raise ValidationError("O grupo não está ativo.")
    project = Project.objects.select_for_update().get(pk=group.project_id)
    if not ProjectForwarding.objects.filter(project=project).exists():
        raise ValidationError("O projeto precisa ser encaminhado antes de designar.")
    try:
        professor = ProfessorProfile.objects.select_related("user").get(
            pk=professor_profile_id, user__is_active=True
        )
    except ProfessorProfile.DoesNotExist as error:
        raise ValidationError("Professor indisponível para avaliação.") from error
    if professor.pk in orientador_profile_ids(project):
        raise PermissionDenied("O orientador não pode avaliar a própria sala.")
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
        raise ValidationError(
            {"justification": "Justifique a designação fora da recomendação."}
        )
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
    audit(
        actor, "DESIGNATE_EVALUATOR", group, ["evaluator", "justification"]
    )
    record_event(
        actor,
        project,
        "EVALUATOR_DESIGNATED",
        "",
        professor.user.get_full_name(),
        justification or "Avaliador designado pela secretaria.",
    )
    from accounts.models import Notification
    from accounts.notifications import notify

    notify(
        professor.user,
        Notification.Kind.EVALUATOR_DESIGNATED,
        f"Você foi designado avaliador de {project.name}",
        justification or "Designação da secretaria.",
        project=project,
    )
    return assignment
