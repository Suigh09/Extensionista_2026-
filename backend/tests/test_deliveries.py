# ruff: noqa: F811 - academic_context e fixture pytest importada de test_projects;
# o parametro homonimo nos testes registra o uso como fixture, nao como redefinicao.
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from projects.models import (
    ActiveGroupSlot,
    FormalDelivery,
    GroupMember,
    Project,
    ProjectGroup,
)
from rest_framework.test import APIClient

from .test_projects import academic_context, create_project  # noqa: F401

PDF_BYTES = b"%PDF-1.4 entrega formal de teste"


def pdf(name="entrega.pdf"):
    return SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf")


def setup(academic_context):
    offering, _, student = academic_context
    _, profile, client = student(1)
    _, outsider_profile, outsider = student(2)
    room = profile.room_memberships.get().room
    teacher = APIClient()
    teacher.force_authenticate(room.responsible_professor.user)
    return offering, profile, client, outsider_profile, outsider, room, teacher


def approved_project(client, offering):
    return create_project(client, offering, approved=True).json()


@pytest.mark.django_db
def test_student_submits_versioned_delivery_with_document(academic_context):
    offering, _, client, _, _, _, _ = setup(academic_context)
    project = approved_project(client, offering)
    first = client.post(
        f"/api/v1/projects/{project['id']}/deliveries/",
        {"notes": "Primeira entrega", "document": pdf()},
        format="multipart",
    )
    assert first.status_code == 201, first.content
    body = first.json()
    assert body["version"] == 1
    assert body["status"] == "SUBMITTED"
    assert body["title_snapshot"] == project["name"]
    assert body["original_name"] == "entrega.pdf"
    listed = client.get(f"/api/v1/projects/{project['id']}/deliveries/")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


@pytest.mark.django_db
def test_delivery_requires_document_and_approved_proposal(academic_context):
    offering, _, client, _, outsider, _, _ = setup(academic_context)
    draft = create_project(outsider, offering, approved=False).json()
    assert (
        outsider.post(
            f"/api/v1/projects/{draft['id']}/deliveries/",
            {"notes": "Rascunho", "document": pdf()},
            format="multipart",
        ).status_code
        == 400
    )
    project = approved_project(client, offering)
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/deliveries/",
            {"notes": "Sem documento"},
            format="multipart",
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/deliveries/",
            {"document": SimpleUploadedFile("x.pdf", b"nao e pdf", "application/pdf")},
            format="multipart",
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/deliveries/",
            {"document": SimpleUploadedFile("x.exe", b"MZ", "application/x-msdownload")},
            format="multipart",
        ).status_code
        == 400
    )


@pytest.mark.django_db
def test_second_submit_blocked_while_pending(academic_context):
    offering, _, client, _, _, _, _ = setup(academic_context)
    project = approved_project(client, offering)
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/deliveries/",
            {"document": pdf()},
            format="multipart",
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/deliveries/",
            {"document": pdf("outra.pdf")},
            format="multipart",
        ).status_code
        == 400
    )


@pytest.mark.django_db
def test_orientador_reviews_and_new_version_follows(academic_context):
    offering, _, client, _, _, _, teacher = setup(academic_context)
    project = approved_project(client, offering)
    delivery = client.post(
        f"/api/v1/projects/{project['id']}/deliveries/",
        {"document": pdf()},
        format="multipart",
    ).json()
    url = f"/api/v1/projects/deliveries/{delivery['id']}/review/"
    assert (
        teacher.post(url, {"decision": "CHANGES_REQUESTED", "feedback": ""}).status_code
        == 400
    )
    changes = teacher.post(
        url, {"decision": "CHANGES_REQUESTED", "feedback": "Melhorar conclusao."}
    )
    assert changes.status_code == 200
    assert changes.json()["status"] == "CHANGES_REQUESTED"
    second = client.post(
        f"/api/v1/projects/{project['id']}/deliveries/",
        {"document": pdf("v2.pdf")},
        format="multipart",
    )
    assert second.status_code == 201
    assert second.json()["version"] == 2
    approved = teacher.post(url.replace(delivery["id"], second.json()["id"]), {
        "decision": "APPROVED",
        "feedback": "Excelente.",
    })
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    history = client.get(f"/api/v1/projects/{project['id']}/deliveries/")
    assert [item["version"] for item in history.json()] == [1, 2]


@pytest.mark.django_db
def test_delivery_endpoints_enforce_object_authorization(academic_context):
    offering, _, client, _, outsider, _, teacher = setup(academic_context)
    project = approved_project(client, offering)
    delivery = client.post(
        f"/api/v1/projects/{project['id']}/deliveries/",
        {"document": pdf()},
        format="multipart",
    ).json()
    assert (
        outsider.get(f"/api/v1/projects/{project['id']}/deliveries/").status_code == 404
    )
    assert (
        outsider.post(
            f"/api/v1/projects/{project['id']}/deliveries/",
            {"document": pdf()},
            format="multipart",
        ).status_code
        == 404
    )
    assert (
        outsider.post(
            f"/api/v1/projects/deliveries/{delivery['id']}/review/",
            {"decision": "APPROVED"},
        ).status_code
        == 403
    )
    assert (
        outsider.get(f"/api/v1/projects/deliveries/{delivery['id']}/download/").status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/projects/deliveries/{delivery['id']}/review/",
            {"decision": "APPROVED"},
        ).status_code
        == 403
    )
    from accounts.models import User as AuthUser

    outsider_professor = APIClient()
    outsider_professor.force_authenticate(
        AuthUser.objects.create_user(
            username="professor-estrangeiro",
            role="PROFESSOR",
            password="test-password-123",
        )
    )
    assert (
        outsider_professor.post(
            f"/api/v1/projects/deliveries/{delivery['id']}/review/",
            {"decision": "APPROVED"},
        ).status_code
        == 403
    )
    assert teacher.post(
        f"/api/v1/projects/{project['id']}/forward/", {}
    ).status_code == 400


@pytest.mark.django_db
def test_forward_requires_approved_delivery_and_lists_queue(academic_context):
    offering, _, client, _, _, _, teacher = setup(academic_context)
    project = approved_project(client, offering)
    delivery = client.post(
        f"/api/v1/projects/{project['id']}/deliveries/",
        {"document": pdf()},
        format="multipart",
    ).json()
    teacher.post(
        f"/api/v1/projects/deliveries/{delivery['id']}/review/",
        {"decision": "APPROVED"},
    )
    payload = {
        "observations": "Turma dedicada.",
        "required_competencies": "Metodologia e escrita.",
    }
    forwarded = teacher.post(
        f"/api/v1/projects/{project['id']}/forward/", payload, format="json"
    )
    assert forwarded.status_code == 201, forwarded.content
    body = forwarded.json()
    assert body["observations"] == "Turma dedicada."
    assert body["required_competencies"] == "Metodologia e escrita."
    assert (
        teacher.post(
            f"/api/v1/projects/{project['id']}/forward/", payload, format="json"
        ).status_code
        == 400
    )
    admin = APIClient()
    from accounts.models import User

    secretary = User.objects.create_user(
        username="secretary-deliveries", role="SECRETARIAT", password="test-password-123"
    )
    admin.force_authenticate(secretary)
    queue = admin.get("/api/v1/projects/forwarded/")
    assert queue.status_code == 200
    assert [item["project"] for item in queue.json()] == [project["id"]]
    download = admin.get(f"/api/v1/projects/deliveries/{delivery['id']}/download/")
    assert download.status_code == 200
    assert client.get(f"/api/v1/projects/{project['id']}/forward/").status_code == 200


@pytest.mark.django_db
def test_forward_requires_both_groups_when_interdisciplinary(academic_context):
    offering, _, client, outsider_profile, _, _, teacher = setup(
        academic_context
    )
    project = approved_project(client, offering)
    delivery = client.post(
        f"/api/v1/projects/{project['id']}/deliveries/",
        {"document": pdf()},
        format="multipart",
    ).json()
    teacher.post(
        f"/api/v1/projects/deliveries/{delivery['id']}/review/",
        {"decision": "APPROVED"},
    )
    instance = Project.objects.get(pk=project["id"])
    second_group = ProjectGroup.objects.create(
        project=instance,
        class_offering=offering,
        name="Segundo grupo",
        responsible_professor=instance.groups.get().responsible_professor,
    )
    GroupMember.objects.create(group=second_group, student=outsider_profile)
    ActiveGroupSlot.objects.create(student=outsider_profile, group=second_group)
    response = teacher.post(f"/api/v1/projects/{project['id']}/forward/", {})
    assert response.status_code == 400
    assert FormalDelivery.objects.filter(project=instance).count() == 1
