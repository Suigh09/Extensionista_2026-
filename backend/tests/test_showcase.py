# ruff: noqa: F811 - academic_context e fixture pytest importada de test_projects;
# o parametro homonimo nos testes registra o uso como fixture, nao como redefinicao.
import pytest
from accounts.models import AuditEvent, User
from django.core.files.uploadedfile import SimpleUploadedFile
from projects.models import (
    ProjectGroup,
    Publication,
    ShowcaseEntry,
)
from rest_framework.test import APIClient

from .test_projects import academic_context, create_project  # noqa: F401

PDF_BYTES = b"%PDF-1.4 documento publicavel de teste"


def pdf(name="documento.pdf"):
    return SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf")


def setup(academic_context):
    offering, _, student = academic_context
    _, profile, client = student(1)
    _, outsider_profile, outsider = student(2)
    room = profile.room_memberships.get().room
    teacher = APIClient()
    teacher.force_authenticate(room.responsible_professor.user)
    secretary = APIClient()
    secretary.force_authenticate(
        User.objects.create_user(
            username="secretary-showcase", role="SECRETARIAT", password="test-password-123"
        )
    )
    admin = APIClient()
    admin.force_authenticate(
        User.objects.create_user(
            username="admin-showcase", role="ADMIN", password="test-password-123"
        )
    )
    outsider_professor = APIClient()
    outsider_professor.force_authenticate(
        User.objects.create_user(
            username="professor-estrangeiro-showcase",
            role="PROFESSOR",
            password="test-password-123",
        )
    )
    return (
        offering,
        profile,
        client,
        outsider_profile,
        outsider,
        room,
        teacher,
        secretary,
        admin,
        outsider_professor,
    )


def approved_project(client, offering):
    return create_project(client, offering, approved=True).json()


def evaluator_of(project_id):
    instance = ProjectGroup.objects.filter(project_id=project_id).first()
    return instance.evaluator.user if instance and instance.evaluator else None


def set_evaluator(project_id, evaluator_user):
    instance = ProjectGroup.objects.filter(project_id=project_id).first()
    if instance:
        profile = evaluator_user.professor_profile
        instance.evaluator = profile
        instance.save(update_fields=["evaluator"])


@pytest.mark.django_db
def test_secretariat_schedules_showcase(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    set_evaluator(project["id"], teacher.handler._force_user)
    response = secretary.post(
        "/api/v1/projects/showcase/",
        {
            "group": project["groups"][0]["id"],
            "date": "2026-12-10T14:00:00Z",
            "location": "Auditório Central",
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["status"] == "SCHEDULED"
    assert body["location"] == "Auditório Central"
    assert AuditEvent.objects.filter(action="SCHEDULE_SHOWCASE").exists()


@pytest.mark.django_db
def test_evaluator_records_presence(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    set_evaluator(project["id"], teacher.handler._force_user)
    secretary.post(
        "/api/v1/projects/showcase/",
        {
            "group": project["groups"][0]["id"],
            "date": "2026-12-10T14:00:00Z",
            "location": "Auditório Central",
        },
        format="json",
    )
    entry = ShowcaseEntry.objects.get(group__project_id=project["id"])
    response = teacher.post(
        f"/api/v1/projects/showcase/{entry.id}/",
        {"status": "PRESENTED", "notes": "Apresentou o trabalho."},
        format="json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["status"] == "PRESENTED"
    assert AuditEvent.objects.filter(action="RECORD_PRESENTED").exists()


@pytest.mark.django_db
def test_student_cannot_record_presence(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    set_evaluator(project["id"], teacher.handler._force_user)
    secretary.post(
        "/api/v1/projects/showcase/",
        {
            "group": project["groups"][0]["id"],
            "date": "2026-12-10T14:00:00Z",
            "location": "Auditório Central",
        },
        format="json",
    )
    entry = ShowcaseEntry.objects.get(group__project_id=project["id"])
    response = client.post(
        f"/api/v1/projects/showcase/{entry.id}/",
        {"status": "PRESENTED"},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_student_generates_document_with_consent(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    response = client.post(
        f"/api/v1/projects/{project['id']}/publication-documents/",
        {"pdf": pdf(), "consent_given": "true"},
        format="multipart",
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["version"] == 1
    assert body["status"] == "PENDING"
    assert body["consent_given"] is True
    assert body["download_url"]
    assert AuditEvent.objects.filter(action="GENERATE_PUBLICATION_DOCUMENT").exists()


@pytest.mark.django_db
def test_document_versioning(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    client.post(
        f"/api/v1/projects/{project['id']}/publication-documents/",
        {"pdf": pdf(), "consent_given": "true"},
        format="multipart",
    )
    second = client.post(
        f"/api/v1/projects/{project['id']}/publication-documents/",
        {"pdf": pdf("v2.pdf"), "consent_given": "true"},
        format="multipart",
    )
    assert second.status_code == 201, second.content
    assert second.json()["version"] == 2


@pytest.mark.django_db
def test_orientador_approves_document(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    doc = client.post(
        f"/api/v1/projects/{project['id']}/publication-documents/",
        {"pdf": pdf(), "consent_given": "true"},
        format="multipart",
    ).json()
    response = teacher.post(
        f"/api/v1/projects/publication-documents/{doc['id']}/review/",
        {"status": "APPROVED", "review": "Documento conforme template institucional."},
        format="json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["status"] == "APPROVED"
    assert AuditEvent.objects.filter(action="REVIEW_DOCUMENT_APPROVED").exists()


@pytest.mark.django_db
def test_non_orientador_cannot_review_document(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, outsider_professor = setup(
        academic_context
    )
    project = approved_project(client, academic_context[0])
    doc = client.post(
        f"/api/v1/projects/{project['id']}/publication-documents/",
        {"pdf": pdf(), "consent_given": "true"},
        format="multipart",
    ).json()
    response = outsider_professor.post(
        f"/api/v1/projects/publication-documents/{doc['id']}/review/",
        {"status": "APPROVED", "review": "Aprovado."},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_student_publishes_project_gf09(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    set_evaluator(project["id"], teacher.handler._force_user)
    secretary.post(
        "/api/v1/projects/showcase/",
        {
            "group": project["groups"][0]["id"],
            "date": "2026-12-10T14:00:00Z",
            "location": "Auditório Central",
        },
        format="json",
    )
    entry = ShowcaseEntry.objects.get(group__project_id=project["id"])
    teacher.post(
        f"/api/v1/projects/showcase/{entry.id}/",
        {"status": "PRESENTED"},
        format="json",
    )
    doc = client.post(
        f"/api/v1/projects/{project['id']}/publication-documents/",
        {"pdf": pdf(), "consent_given": "true"},
        format="multipart",
    ).json()
    teacher.post(
        f"/api/v1/projects/publication-documents/{doc['id']}/review/",
        {"status": "APPROVED", "review": "OK"},
        format="json",
    )
    response = client.post(
        "/api/v1/projects/publications/",
        {"project": project["id"], "document": doc["id"]},
        format="json",
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["is_published"] is True
    assert body["document_version"] == 1
    assert Publication.objects.filter(project_id=project["id"]).exists()
    assert AuditEvent.objects.filter(action="PUBLISH_PROJECT").exists()


@pytest.mark.django_db
def test_publication_blocked_when_not_presented_gf10(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    doc = client.post(
        f"/api/v1/projects/{project['id']}/publication-documents/",
        {"pdf": pdf(), "consent_given": "true"},
        format="multipart",
    ).json()
    teacher.post(
        f"/api/v1/projects/publication-documents/{doc['id']}/review/",
        {"status": "APPROVED", "review": "OK"},
        format="json",
    )
    response = client.post(
        "/api/v1/projects/publications/",
        {"project": project["id"], "document": doc["id"]},
        format="json",
    )
    assert response.status_code == 400, response.content
    body = response.json()
    mensagem = str(body).lower()
    assert "apresentado" in mensagem


@pytest.mark.django_db
def test_publication_blocked_when_document_not_approved(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    set_evaluator(project["id"], teacher.handler._force_user)
    secretary.post(
        "/api/v1/projects/showcase/",
        {
            "group": project["groups"][0]["id"],
            "date": "2026-12-10T14:00:00Z",
            "location": "Auditório Central",
        },
        format="json",
    )
    entry = ShowcaseEntry.objects.get(group__project_id=project["id"])
    teacher.post(
        f"/api/v1/projects/showcase/{entry.id}/",
        {"status": "PRESENTED"},
        format="json",
    )
    doc = client.post(
        f"/api/v1/projects/{project['id']}/publication-documents/",
        {"pdf": pdf(), "consent_given": "true"},
        format="multipart",
    ).json()
    response = client.post(
        "/api/v1/projects/publications/",
        {"project": project["id"], "document": doc["id"]},
        format="json",
    )
    assert response.status_code == 400, response.content
    body = response.json()
    mensagem = str(body).lower()
    assert "aprovado" in mensagem


@pytest.mark.django_db
def test_publication_blocked_without_consent(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    set_evaluator(project["id"], teacher.handler._force_user)
    secretary.post(
        "/api/v1/projects/showcase/",
        {
            "group": project["groups"][0]["id"],
            "date": "2026-12-10T14:00:00Z",
            "location": "Auditório Central",
        },
        format="json",
    )
    entry = ShowcaseEntry.objects.get(group__project_id=project["id"])
    teacher.post(
        f"/api/v1/projects/showcase/{entry.id}/",
        {"status": "PRESENTED"},
        format="json",
    )
    doc = client.post(
        f"/api/v1/projects/{project['id']}/publication-documents/",
        {"pdf": pdf()},
        format="multipart",
    ).json()
    teacher.post(
        f"/api/v1/projects/publication-documents/{doc['id']}/review/",
        {"status": "APPROVED", "review": "OK"},
        format="json",
    )
    response = client.post(
        "/api/v1/projects/publications/",
        {"project": project["id"], "document": doc["id"]},
        format="json",
    )
    assert response.status_code == 400, response.content
    body = response.json()
    mensagem = str(body).lower()
    assert "consentimento" in mensagem


@pytest.mark.django_db
def test_secretariat_withdraws_publication(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    set_evaluator(project["id"], teacher.handler._force_user)
    secretary.post(
        "/api/v1/projects/showcase/",
        {
            "group": project["groups"][0]["id"],
            "date": "2026-12-10T14:00:00Z",
            "location": "Auditório Central",
        },
        format="json",
    )
    entry = ShowcaseEntry.objects.get(group__project_id=project["id"])
    teacher.post(
        f"/api/v1/projects/showcase/{entry.id}/",
        {"status": "PRESENTED"},
        format="json",
    )
    doc = client.post(
        f"/api/v1/projects/{project['id']}/publication-documents/",
        {"pdf": pdf(), "consent_given": "true"},
        format="multipart",
    ).json()
    teacher.post(
        f"/api/v1/projects/publication-documents/{doc['id']}/review/",
        {"status": "APPROVED", "review": "OK"},
        format="json",
    )
    pub = client.post(
        "/api/v1/projects/publications/",
        {"project": project["id"], "document": doc["id"]},
        format="json",
    ).json()
    response = secretary.post(
        f"/api/v1/projects/publications/{pub['id']}/withdraw/",
        {"reason": "Solicitação do autor."},
        format="json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["withdrawn_at"] is not None
    assert response.json()["withdrawal_reason"] == "Solicitação do autor."
    assert AuditEvent.objects.filter(action="WITHDRAW_PUBLICATION").exists()
    # Item sai da consulta do acervo (nao publicado mais)
    acervo = client.get("/api/v1/projects/acervo/")
    assert all(item["id"] != pub["id"] for item in acervo.json())


@pytest.mark.django_db
def test_student_cannot_withdraw_publication(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    set_evaluator(project["id"], teacher.handler._force_user)
    secretary.post(
        "/api/v1/projects/showcase/",
        {
            "group": project["groups"][0]["id"],
            "date": "2026-12-10T14:00:00Z",
            "location": "Auditório Central",
        },
        format="json",
    )
    entry = ShowcaseEntry.objects.get(group__project_id=project["id"])
    teacher.post(
        f"/api/v1/projects/showcase/{entry.id}/",
        {"status": "PRESENTED"},
        format="json",
    )
    doc = client.post(
        f"/api/v1/projects/{project['id']}/publication-documents/",
        {"pdf": pdf(), "consent_given": "true"},
        format="multipart",
    ).json()
    teacher.post(
        f"/api/v1/projects/publication-documents/{doc['id']}/review/",
        {"status": "APPROVED", "review": "OK"},
        format="json",
    )
    pub = client.post(
        "/api/v1/projects/publications/",
        {"project": project["id"], "document": doc["id"]},
        format="json",
    ).json()
    response = client.post(
        f"/api/v1/projects/publications/{pub['id']}/withdraw/",
        {"reason": "Quero retirar."},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_acervo_returns_only_published_projects(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    set_evaluator(project["id"], teacher.handler._force_user)
    secretary.post(
        "/api/v1/projects/showcase/",
        {
            "group": project["groups"][0]["id"],
            "date": "2026-12-10T14:00:00Z",
            "location": "Auditório Central",
        },
        format="json",
    )
    entry = ShowcaseEntry.objects.get(group__project_id=project["id"])
    teacher.post(
        f"/api/v1/projects/showcase/{entry.id}/",
        {"status": "PRESENTED"},
        format="json",
    )
    doc = client.post(
        f"/api/v1/projects/{project['id']}/publication-documents/",
        {"pdf": pdf(), "consent_given": "true"},
        format="multipart",
    ).json()
    teacher.post(
        f"/api/v1/projects/publication-documents/{doc['id']}/review/",
        {"status": "APPROVED", "review": "OK"},
        format="json",
    )
    client.post(
        "/api/v1/projects/publications/",
        {"project": project["id"], "document": doc["id"]},
        format="json",
    )
    response = client.get("/api/v1/projects/acervo/")
    assert response.status_code == 200
    names = [item["project_name"] for item in response.json()]
    assert project["name"] in names
    # Minimizacao LGPD: so metadados, nao dados pessoais dos alunos
    for item in response.json():
        assert "student_name" not in item
        assert "ra" not in item


@pytest.mark.django_db
def test_showcase_entry_idempotency_one_per_group(academic_context):
    _, _, client, _, _, _, teacher, secretary, _, _ = setup(academic_context)
    project = approved_project(client, academic_context[0])
    secretary.post(
        "/api/v1/projects/showcase/",
        {
            "group": project["groups"][0]["id"],
            "date": "2026-12-10T14:00:00Z",
            "location": "Auditório Central",
        },
        format="json",
    )
    response = secretary.post(
        "/api/v1/projects/showcase/",
        {
            "group": project["groups"][0]["id"],
            "date": "2026-12-11T14:00:00Z",
            "location": "Outro local",
        },
        format="json",
    )
    assert response.status_code == 400, response.content
    assert ShowcaseEntry.objects.filter(group__project_id=project["id"]).count() == 1
