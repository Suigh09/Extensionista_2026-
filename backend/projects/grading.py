"""Group and individual grading (Sprint 6)."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from academic.models import ProfessorProfile
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from .lifecycle import record_event, require_mutable
from .models import (
    Criterion,
    GradeItem,
    GradeSubmission,
    GroupMember,
    IndividualGrade,
    Project,
    ProjectForwarding,
    ProjectGroup,
    Rubric,
)
from .services import audit


def owner_profile(actor):
    if actor.role != "PROFESSOR":
        return None
    return ProfessorProfile.objects.filter(user=actor).first()


def parse_score(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise ValidationError("Nota inválida: use número de 0 a 10.") from error
    if number.is_nan() or number < 0 or number > 10:
        raise ValidationError("Nota inválida: use número de 0 a 10.")
    return number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def group_grade_value(group):
    latest = (
        GradeSubmission.objects.filter(group=group).order_by("-created_at", "-id").first()
    )
    if latest is None:
        return None, None
    items = list(latest.items.all())
    if not items:
        return None, latest
    total = sum((item.value for item in items), Decimal("0"))
    average = (total / len(items)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return average, latest


@transaction.atomic
def create_rubric(*, actor, title, criteria):
    profile = owner_profile(actor)
    if profile is None:
        raise PermissionDenied("Somente professor ativo gerencia rubricas.")
    title = str(title or "").strip()
    if not title:
        raise ValidationError({"title": "Informe o título da rubrica."})
    names = [str(item.get("name", "")).strip() for item in criteria or []]
    if not names or any(not name for name in names):
        raise ValidationError({"criteria": "Informe ao menos um critério nomeado."})
    if len(set(names)) != len(names):
        raise ValidationError({"criteria": "Critérios duplicados."})
    rubric = Rubric.objects.create(owner=profile, title=title[:160])
    for position, item in enumerate(criteria):
        Criterion.objects.create(
            rubric=rubric,
            name=str(item.get("name", "")).strip()[:160],
            description=str(item.get("description", "")).strip(),
            position=position,
        )
    audit(actor, "CREATE_RUBRIC", rubric, ["title", "criteria"])
    return rubric


def _owned_rubric(actor, rubric_id):
    profile = owner_profile(actor)
    if profile is None:
        raise PermissionDenied("Somente professor ativo gerencia rubricas.")
    try:
        return Rubric.objects.get(pk=rubric_id, owner=profile)
    except Rubric.DoesNotExist as error:
        raise ValidationError("Rubrica indisponível.") from error


@transaction.atomic
def update_rubric_title(*, actor, rubric, title):
    rubric = _owned_rubric(actor, rubric.pk)
    title = str(title or "").strip()
    if not title:
        raise ValidationError({"title": "Informe o título da rubrica."})
    rubric.title = title[:160]
    rubric.save(update_fields=["title", "updated_at"])
    return rubric


@transaction.atomic
def add_criterion(*, actor, rubric, name, description=""):
    rubric = _owned_rubric(actor, rubric.pk)
    name = str(name or "").strip()
    if not name:
        raise ValidationError({"name": "Informe o nome do critério."})
    criterion = Criterion.objects.create(
        rubric=rubric,
        name=name[:160],
        description=str(description or "").strip(),
        position=rubric.criteria.count(),
    )
    return criterion


@transaction.atomic
def delete_criterion(*, actor, criterion):
    rubric = _owned_rubric(actor, criterion.rubric_id)
    criterion = Criterion.objects.get(pk=criterion.pk, rubric=rubric)
    if GradeItem.objects.filter(criterion=criterion).exists():
        raise ValidationError("Critério já utilizado em avaliações.")
    criterion.delete()


def usable_rubrics(actor, project):
    profile = owner_profile(actor)
    owners = set(
        project.groups.filter(is_active=True).exclude(
            responsible_professor__isnull=True
        ).values_list("responsible_professor_id", flat=True)
    )
    if profile is not None:
        owners.add(profile.pk)
    evaluator_groups = project.groups.filter(is_active=True, evaluator=profile).values_list(
        "responsible_professor_id", flat=True
    )
    owners.update(evaluator_groups)
    return Rubric.objects.filter(owner_id__in=owners).order_by("title", "id")


def _evaluator_group(actor, group):
    group = ProjectGroup.objects.select_related(
        "project", "evaluator__user", "responsible_professor__user"
    ).get(pk=group.pk)
    if not group.is_active:
        raise ValidationError("O grupo não está ativo.")
    if group.evaluator is None or group.evaluator.user_id != actor.pk:
        raise PermissionDenied("Somente o avaliador designado avalia este grupo.")
    return group


@transaction.atomic
def submit_grades(*, actor, group, rubric_id, items, comment=""):
    group = _evaluator_group(actor, group)
    project = Project.objects.select_for_update().get(pk=group.project_id)
    require_mutable(project)
    if not ProjectForwarding.objects.filter(project=project).exists():
        raise ValidationError("O projeto precisa ser encaminhado antes de avaliar.")
    latest = (
        GradeSubmission.objects.filter(group=group)
        .order_by("-created_at", "-id")
        .first()
    )
    if latest is not None and latest.concluded:
        raise ValidationError("Avaliação concluída não recebe novas notas.")
    try:
        rubric = Rubric.objects.prefetch_related("criteria").get(pk=rubric_id)
    except (Rubric.DoesNotExist, ValueError, TypeError) as error:
        raise ValidationError("Rubrica indisponível.") from error
    expected = {str(item.pk): item for item in rubric.criteria.all()}
    if not expected:
        raise ValidationError("A rubrica não possui critérios.")
    supplied = {}
    for entry in items or []:
        key = str(entry.get("criterion", ""))
        if key in supplied or key not in expected:
            raise ValidationError("Critérios inválidos: avalie todos, sem repetir.")
        supplied[key] = parse_score(entry.get("value"))
    if set(supplied) != set(expected):
        raise ValidationError("Avalie todos os critérios da rubrica.")
    submission = GradeSubmission.objects.create(
        group=group,
        rubric=rubric,
        author=actor,
        comment=str(comment or "").strip()[:2000],
    )
    GradeItem.objects.bulk_create(
        [
            GradeItem(submission=submission, criterion=expected[key], value=value)
            for key, value in supplied.items()
        ]
    )
    record_event(
        actor,
        project,
        "GRADES_SUBMITTED",
        "",
        group.name or "grupo",
        f"Notas lançadas para {group.name or 'o grupo'}.",
    )
    return submission


@transaction.atomic
def conclude_evaluation(*, actor, group):
    group = _evaluator_group(actor, group)
    project = Project.objects.select_for_update().get(pk=group.project_id)
    require_mutable(project)
    latest = (
        GradeSubmission.objects.select_for_update()
        .filter(group=group)
        .order_by("-created_at", "-id")
        .first()
    )
    if latest is None:
        raise ValidationError("Lance as notas antes de concluir.")
    if latest.concluded:
        raise ValidationError("Avaliação já concluída.")
    latest.concluded = True
    latest.save(update_fields=["concluded"])
    record_event(
        actor, project, "EVALUATION_CONCLUDED", "", group.name or "grupo",
        "Avaliação do grupo concluída.",
    )
    from accounts.models import Notification
    from accounts.notifications import notify

    members = GroupMember.objects.filter(
        group=group, is_active=True
    ).select_related("student__user")
    notify(
        [member.student.user for member in members],
        Notification.Kind.EVALUATION_CONCLUDED,
        f"Avaliação concluída em {project.name}",
        "Confira suas notas e comentários.",
        project=project,
    )
    return latest


@transaction.atomic
def grade_student(*, actor, student_id, value, comment=""):
    from academic.models import StudentProfile

    try:
        student = StudentProfile.objects.select_related("user").get(pk=student_id)
    except (StudentProfile.DoesNotExist, ValueError, TypeError) as error:
        raise ValidationError("Aluno indisponível.") from error
    membership = (
        GroupMember.objects.select_related("group__project", "group__responsible_professor")
        .filter(group__is_active=True, is_active=True, student=student)
        .first()
    )
    if membership is None:
        raise ValidationError("Aluno sem grupo vigente.")
    professor = membership.group.responsible_professor
    if (
        actor.role != "PROFESSOR"
        or professor is None
        or professor.user_id != actor.pk
    ):
        raise PermissionDenied("Somente o orientador atribui notas individuais.")
    grade = IndividualGrade.objects.create(
        student=student,
        group=membership.group,
        value=parse_score(value),
        comment=str(comment or "").strip()[:2000],
        author=actor,
    )
    audit(actor, "INDIVIDUAL_GRADE", grade, ["student", "value"])
    return grade


def current_individual(student):
    return (
        IndividualGrade.objects.filter(student=student)
        .order_by("-created_at", "-id")
        .first()
    )
