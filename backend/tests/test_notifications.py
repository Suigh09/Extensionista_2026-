# ruff: noqa: F811 - academic_context e fixture pytest importada de test_projects;
# o parametro homonimo nos testes registra o uso como fixture, nao como redefinicao.
import pytest
from academic.models import AcademicRoom, StudentProfile
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
    secretary = User.objects.create_user(
        username="secretary-notifications",
        role="SECRETARIAT",
        password="test-password-123",
    )
    secretary_client = APIClient()
    secretary_client.force_authenticate(secretary)
    return offering, profile, client, second, second_client, room, teacher, secretary_client


def unread(user, kind=None):
    items = Notification.objects.filter(user=user, is_read=False)
    if kind is not None:
        items = items.filter(kind=kind)
    return items


@pytest.mark.django_db
def test_invitation_notifies_and_read_endpoints_scope(academic_context):
    _, _, client, second, second_client, _, _, _ = setup(academic_context)
    offering = second.class_offering
    project = create_project(client, offering, approved=False).json()
    add_member(client, project["id"], second, second_client)

    notes = unread(second.user, Notification.Kind.GROUP_INVITATION)
    assert notes.count() == 1
    assert project["name"] in notes.first().title

    mine = second_client.get("/api/v1/auth/notifications/")
    assert mine.status_code == 200
    assert [item["kind"] for item in mine.json()] == ["GROUP_INVITATION"]

    stranger = APIClient()
    stranger.force_authenticate(
        User.objects.create_user(
            username="stranger-notifications",
            role="STUDENT",
            password="test-password-123",
        )
    )
    assert stranger.get("/api/v1/auth/notifications/").json() == []
    note_id = mine.json()[0]["id"]
    assert stranger.post(f"/api/v1/auth/notifications/{note_id}/read/").status_code == 404
    assert (
        second_client.post(f"/api/v1/auth/notifications/{note_id}/read/").status_code
        == 200
    )
    assert unread(second.user).count() == 0
    assert (
        second_client.post("/api/v1/auth/notifications/read-all/").status_code == 204
    )


@pytest.mark.django_db
def test_room_pull_transfer_and_decision_notify(academic_context):
    _, _, _, second, _, room, teacher, secretary_client = setup(academic_context)
    newcomer = User.objects.create_user(
        username="newcomer-notifications", role="STUDENT", password="test-password-123"
    )
    fresh = StudentProfile.objects.create(
        user=newcomer, ra="RA9001", cpf_hash="x" * 64, cpf_last4="9001"
    )
    added = teacher.post(
        f"/api/v1/academic/rooms/{room.pk}/pull-student/",
        {"student": str(fresh.pk)},
        format="json",
    )
    assert added.status_code == 201
    assert unread(newcomer, Notification.Kind.ROOM_INCLUDED).count() == 1

    other_room = AcademicRoom.objects.create(
        name="Sala destino", responsible_professor=room.responsible_professor
    )
    requested = teacher.post(
        f"/api/v1/academic/rooms/{other_room.pk}/pull-student/",
        {"student": str(second.pk)},
        format="json",
    )
    assert requested.status_code == 202
    assert unread(second.user, Notification.Kind.ROOM_TRANSFER_REQUESTED).count() == 1
    assert Notification.objects.filter(
        user__role="SECRETARIAT",
        kind=Notification.Kind.ROOM_TRANSFER_REQUESTED,
    ).exists()

    from academic.models import RoomTransferRequest

    transfer = RoomTransferRequest.objects.get(
        student=second, status=RoomTransferRequest.Status.PENDING
    )
    decided = secretary_client.post(
        f"/api/v1/academic/room-transfer-requests/{transfer.pk}/approve/",
        {"decision_note": "ok"},
        format="json",
    )
    assert decided.status_code == 200
    assert unread(second.user, Notification.Kind.ROOM_TRANSFER_DECIDED).count() == 1


@pytest.mark.django_db
def test_review_delivery_and_forward_notify(academic_context):
    offering, profile, client, second, second_client, room, teacher, _ = setup(
        academic_context
    )
    project = create_project(client, offering, approved=False).json()
    add_member(client, project["id"], second, second_client)
    assert (
        client.post(f"/api/v1/projects/{project['id']}/submit/", {}, format="json").status_code
        == 200
    )
    assert (
        teacher.post(
            f"/api/v1/projects/{project['id']}/request-changes/",
            {"feedback": "Ajustar escopo."},
            format="json",
        ).status_code
        == 200
    )
    assert (
        unread(second.user, Notification.Kind.PROJECT_ADJUSTMENT_REQUESTED).count() == 1
    )
    assert (
        client.post(f"/api/v1/projects/{project['id']}/submit/", {}, format="json").status_code
        == 200
    )
    assert (
        teacher.post(
            f"/api/v1/projects/{project['id']}/approve/",
            {"feedback": "Aprovado."},
            format="json",
        ).status_code
        == 200
    )

    delivered = client.post(
        f"/api/v1/projects/{project['id']}/deliveries/",
        {
            "notes": "v1",
            "document": SimpleUploadedFile(
                "entrega.pdf", b"%PDF-1.4 teste", content_type="application/pdf"
            ),
        },
        format="multipart",
    )
    assert delivered.status_code == 201, delivered.content
    orientador = room.responsible_professor.user
    assert unread(orientador, Notification.Kind.DELIVERY_SUBMITTED).count() == 1

    delivery_id = delivered.json()["id"]
    assert (
        teacher.post(
            f"/api/v1/projects/deliveries/{delivery_id}/review/",
            {"decision": "APPROVED", "feedback": "Ok."},
            format="json",
        ).status_code
        == 200
    )
    forwarded = teacher.post(
        f"/api/v1/projects/{project['id']}/forward/",
        {"observations": "Boa turma.", "required_competencies": "Metodologia."},
        format="json",
    )
    assert forwarded.status_code == 201, forwarded.content
    assert Notification.objects.filter(
        user__role="SECRETARIAT", kind=Notification.Kind.PROJECT_FORWARDED
    ).exists()
