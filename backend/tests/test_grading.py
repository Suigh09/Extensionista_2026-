# ruff: noqa: F811 - academic_context e fixture pytest importada de test_projects;
# o parametro homonimo nos testes registra o uso como fixture, nao como redefinicao.
import pytest
from academic.models import ProfessorProfile
from accounts.models import Notification, User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from .test_projects import academic_context, add_member, create_project  # noqa: F401


def setup(academic_context):
    offering, _, student = academic_context
    _, profile, client = student(1)
    _, second, second_client = student(2)
    room = profile.room_memberships.get().room
    teacher = APIClient()
    teacher.force_authenticate(room.responsible_professor.user)
    evaluator_user = User.objects.create_user(
        username="evaluator-grading", role="PROFESSOR", password="test-password-123"
    )
    evaluator_profile, _ = ProfessorProfile.objects.get_or_create(user=evaluator_user)
    evaluator = APIClient()
    evaluator.force_authenticate(evaluator_user)
    secretary = User.objects.create_user(
        username="secretary-grading", role="SECRETARIAT", password="test-password-123"
    )
    secretary_client = APIClient()
    secretary_client.force_authenticate(secretary)
    return (
        offering, profile, client, second, second_client, room, teacher,
        evaluator, evaluator_profile, secretary_client,
    )


def ready_group(
    client, second_client, offering, teacher, second, secretary_client, evaluator_profile
):
    project = create_project(client, offering, approved=False).json()
    add_member(client, project["id"], second, second_client)
    assert (
        client.post(f"/api/v1/projects/{project['id']}/submit/", {}, format="json").status_code
        == 200
    )
    assert (
        teacher.post(
            f"/api/v1/projects/{project['id']}/approve/", {"feedback": "Ok."}, format="json"
        ).status_code
        == 200
    )
    delivered = client.post(
        f"/api/v1/projects/{project['id']}/deliveries/",
        {
            "document": SimpleUploadedFile(
                "entrega.pdf", b"%PDF-1.4 teste", content_type="application/pdf"
            )
        },
        format="multipart",
    )
    assert delivered.status_code == 201
    delivery_id = delivered.json()["id"]
    assert (
        teacher.post(
            f"/api/v1/projects/deliveries/{delivery_id}/review/",
            {"decision": "APPROVED"},
            format="json",
        ).status_code
        == 200
    )
    assert (
        teacher.post(
            f"/api/v1/projects/{project['id']}/forward/",
            {"observations": "", "required_competencies": ""},
            format="json",
        ).status_code
        == 201
    )
    from projects.models import Project

    instance = Project.objects.get(pk=project["id"])
    group_id = str(instance.groups.filter(is_active=True).first().pk)
    designated = secretary_client.post(
        f"/api/v1/projects/groups/{group_id}/designate-evaluator/",
        {"professor": str(evaluator_profile.pk), "justification": "Teste."},
        format="json",
    )
    assert designated.status_code == 201, designated.content
    return project["id"], group_id


@pytest.mark.django_db
def test_rubric_crud_and_protected_criterion(academic_context):
    _, _, _, _, _, _, teacher, _, _, _ = setup(academic_context)
    created = teacher.post(
        "/api/v1/projects/rubrics/",
        {"title": "Rubrica", "criteria": [{"name": "Clareza"}, {"name": "Impacto"}]},
        format="json",
    )
    assert created.status_code == 201, created.content
    rubric_id = created.json()["id"]
    assert len(created.json()["criteria"]) == 2
    assert (
        teacher.post(
            "/api/v1/projects/rubrics/",
            {"title": "Vazia", "criteria": []},
            format="json",
        ).status_code
        == 400
    )
    renamed = teacher.patch(
        f"/api/v1/projects/rubrics/{rubric_id}/", {"title": "Rubrica v2"}, format="json"
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Rubrica v2"
    listed = teacher.get("/api/v1/projects/rubrics/")
    assert [item["id"] for item in listed.json()] == [rubric_id]


@pytest.mark.django_db
def test_grades_average_conclude_and_lock(academic_context):
    unpacked = setup(academic_context)
    _, _, client, second, second_client, _, teacher = unpacked[:7]
    evaluator, evaluator_profile, secretary_client = unpacked[7:10]
    offering = second.class_offering
    project_id, group_id = ready_group(
        client, second_client, offering, teacher, second, secretary_client,
        evaluator_profile,
    )

    rubric = teacher.post(
        "/api/v1/projects/rubrics/",
        {"title": "R", "criteria": [{"name": "A"}, {"name": "B"}]},
        format="json",
    ).json()
    criteria = {item["name"]: item["id"] for item in rubric["criteria"]}
    payload = {
        "rubric": rubric["id"],
        "comment": "Bom trabalho.",
        "items": [
            {"criterion": criteria["A"], "value": "8.12"},
            {"criterion": criteria["B"], "value": "8.13"},
        ],
    }
    first = evaluator.post(f"/api/v1/projects/groups/{group_id}/grades/", payload, format="json")
    assert first.status_code == 201, first.content
    assert first.json()["average"] == "8.13"
    assert (
        evaluator.post(
            f"/api/v1/projects/groups/{group_id}/grades/",
            {**payload, "items": [
                {"criterion": criteria["A"], "value": "11"},
                {"criterion": criteria["B"], "value": "8"},
            ]},
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/projects/groups/{group_id}/grades/", payload, format="json"
        ).status_code
        == 403
    )
    history = evaluator.get(f"/api/v1/projects/groups/{group_id}/grades/")
    assert history.json()["average"] == "8.13"
    assert len(history.json()["submissions"]) == 1
    assert (
        evaluator.post(f"/api/v1/projects/groups/{group_id}/conclude/", {}).status_code
        == 200
    )
    locked = evaluator.post(
        f"/api/v1/projects/groups/{group_id}/grades/", payload, format="json"
    )
    assert locked.status_code == 400
    assert Notification.objects.filter(
        kind=Notification.Kind.EVALUATION_CONCLUDED
    ).count() >= 1


@pytest.mark.django_db
def test_individual_grades_by_orientador_with_history(academic_context):
    _, profile, client, second, second_client, _, teacher, _, _, _ = setup(
        academic_context
    )
    offering = second.class_offering
    project = create_project(client, offering, approved=True).json()
    add_member(client, project["id"], second, second_client)
    payload = {"value": "9.5", "comment": "Destaque."}
    created = teacher.post(
        f"/api/v1/academic/students/{second.pk}/individual-grade/", payload, format="json"
    )
    assert created.status_code == 201, created.content
    assert created.json()["value"] == "9.50"
    second_round = teacher.post(
        f"/api/v1/academic/students/{second.pk}/individual-grade/",
        {"value": "9.0"},
        format="json",
    )
    assert second_round.status_code == 201
    seen = teacher.get(f"/api/v1/academic/students/{second.pk}/individual-grade/")
    assert seen.json()["current"]["value"] == "9.00"
    assert len(seen.json()["history"]) == 2
    assert (
        client.post(
            f"/api/v1/academic/students/{second.pk}/individual-grade/", payload, format="json"
        ).status_code
        == 403
    )
