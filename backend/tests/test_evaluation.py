# ruff: noqa: F811 - academic_context e fixture pytest importada de test_projects;
# o parametro homonimo nos testes registra o uso como fixture, nao como redefinicao.
import pytest
from academic.models import ProfessorExpertise, ProfessorProfile
from accounts.models import Notification, User
from django.core.files.uploadedfile import SimpleUploadedFile
from projects.models import EvaluatorAssignment, Project
from rest_framework.test import APIClient

from .test_projects import academic_context, add_member, create_project  # noqa: F401


def setup(academic_context):
    offering, other, student = academic_context
    _, profile, client = student(1)
    _, second, second_client = student(2)
    room = profile.room_memberships.get().room
    teacher = APIClient()
    teacher.force_authenticate(room.responsible_professor.user)
    secretary = User.objects.create_user(
        username="secretary-evaluation",
        role="SECRETARIAT",
        password="test-password-123",
    )
    secretary_client = APIClient()
    secretary_client.force_authenticate(secretary)
    return offering, other, profile, client, second, second_client, room, teacher, secretary_client


def forwarded_project(client, second_client, offering, teacher, second):
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
    forwarded = teacher.post(
        f"/api/v1/projects/{project['id']}/forward/",
        {"observations": "", "required_competencies": "Metodologia de pesquisa"},
        format="json",
    )
    assert forwarded.status_code == 201
    return Project.objects.get(pk=project["id"])


@pytest.mark.django_db
def test_recommendations_explain_order_and_exclude_orientador(academic_context):
    offering, other, _, client, second, second_client, room, teacher, secretary_client = setup(
        academic_context
    )
    project = forwarded_project(client, second_client, offering, teacher, second)

    table = secretary_client.get(
        f"/api/v1/projects/{project.pk}/evaluator-recommendations/"
    )
    assert table.status_code == 200
    body = table.json()
    assert "metodologia" in body["keywords"]
    assert "pesquisa" in body["keywords"]
    names = [item["name"] for item in body["recommendations"]]
    assert room.responsible_professor.user.get_full_name() not in names

    other_user = User.objects.create_user(
        username="professor-compativel",
        role="PROFESSOR",
        password="test-password-123",
    )
    compatible, _ = ProfessorProfile.objects.get_or_create(user=other_user)
    ProfessorExpertise.objects.create(
        professor=compatible, kind="COMPETENCY", text="Metodologia de Pesquisa"
    )
    table = secretary_client.get(
        f"/api/v1/projects/{project.pk}/evaluator-recommendations/"
    )
    top = table.json()["recommendations"][0]
    assert top["professor_profile_id"] == str(compatible.pk)
    assert "metodologia" in top["matched"]
    assert top["matched"]["metodologia"] == ["Metodologia de Pesquisa"]


@pytest.mark.django_db
def test_designation_rules_justification_history_and_notification(academic_context):
    _, _, _, client, second, second_client, room, teacher, secretary_client = setup(
        academic_context
    )
    project = forwarded_project(client, second_client, second.class_offering, teacher, second)
    group_id = str(project.groups.filter(is_active=True).first().pk)

    other_user = User.objects.create_user(
        username="professor-compativel-2",
        role="PROFESSOR",
        password="test-password-123",
    )
    compatible, _ = ProfessorProfile.objects.get_or_create(user=other_user)
    ProfessorExpertise.objects.create(
        professor=compatible, kind="COMPETENCY", text="Metodologia de Pesquisa"
    )
    plain = User.objects.create_user(
        username="professor-comum", role="PROFESSOR", password="test-password-123"
    )
    plain_profile, _ = ProfessorProfile.objects.get_or_create(user=plain)

    decide = f"/api/v1/projects/groups/{group_id}/designate-evaluator/"
    assert teacher.post(decide, {"professor": str(compatible.pk)}).status_code == 403
    assert (
        client.post(decide, {"professor": str(compatible.pk)}).status_code == 403
    )
    no_reason = secretary_client.post(decide, {"professor": str(plain_profile.pk)})
    assert no_reason.status_code == 400
    first = secretary_client.post(decide, {"professor": str(compatible.pk)})
    assert first.status_code == 201, first.content
    assert first.json()["justification"] == ""
    project.refresh_from_db()
    assert str(project.groups.get().evaluator_id) == str(compatible.pk)
    assert Notification.objects.filter(
        user=compatible.user, kind=Notification.Kind.EVALUATOR_DESIGNATED
    ).exists()

    second_round = secretary_client.post(
        decide,
        {"professor": str(plain_profile.pk), "justification": "Rodízio entre docentes."},
    )
    assert second_round.status_code == 201
    assert EvaluatorAssignment.objects.filter(
        group_id=group_id
    ).count() == 2
    history = secretary_client.get(
        f"/api/v1/projects/{project.pk}/evaluator-recommendations/"
    ).json()["history"]
    assert len(history) == 2
    assert history[0]["justification"] == ""
    assert history[1]["justification"] == "Rodízio entre docentes."


@pytest.mark.django_db
def test_recommendations_require_forwarding_and_search_scopes(academic_context):
    offering, _, _, client, second, second_client, _, _, secretary_client = setup(
        academic_context
    )
    project = create_project(client, offering, approved=True).json()
    assert (
        secretary_client.get(
            f"/api/v1/projects/{project['id']}/evaluator-recommendations/"
        ).status_code
        == 400
    )
    found = secretary_client.get("/api/v1/academic/professors/search/?q=room")
    assert found.status_code == 200
    assert isinstance(found.json(), list)
    assert (
        secretary_client.get("/api/v1/academic/professors/search/?q=x").json() == []
    )
    professor_client = APIClient()
    professor_client.force_authenticate(second.user)
    assert (
        professor_client.get("/api/v1/academic/professors/search/?q=room").status_code
        == 403
    )
