import pytest
from academic.models import (
    AcademicRoom,
    Course,
    ProfessorExpertise,
    ProfessorProfile,
    RoomMembership,
    RoomTransferRequest,
    StudentProfile,
)
from accounts.models import AuditEvent
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


def authenticated(role):
    user = User.objects.create_user(
        username=f"user-{role.lower()}", password="Uma-senha-segura-123", role=role
    )
    client = APIClient()
    client.force_authenticate(user)
    return client


def create_actor(username, role):
    user = User.objects.create_user(
        username=username, password="Uma-senha-segura-123", role=role,
        first_name=username.title(), email=f"{username}@example.test",
    )
    client = APIClient()
    client.force_authenticate(user)
    return user, client


def create_professor(username):
    user, client = create_actor(username, User.Role.PROFESSOR)
    return user, ProfessorProfile.objects.create(user=user), client


def create_student(username, ra):
    user, client = create_actor(username, User.Role.STUDENT)
    profile = StudentProfile.objects.create(
        user=user, ra=ra, cpf_hash=(username + "x" * 64)[:64], cpf_last4="1234"
    )
    return user, profile, client


@pytest.mark.django_db
@pytest.mark.integration
def test_secretariat_manages_course_and_generates_audit():
    client = authenticated(User.Role.SECRETARIAT)
    response = client.post(
        "/api/v1/academic/courses/",
        {"code": "ads", "name": "Análise e Desenvolvimento de Sistemas"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["code"] == "ADS"
    event = AuditEvent.objects.get()
    assert event.action == "CREATE"
    assert "code" in event.changed_fields


@pytest.mark.django_db
@pytest.mark.security
def test_professor_and_student_cannot_manage_academic_records():
    for role in [User.Role.PROFESSOR, User.Role.STUDENT]:
        response = authenticated(role).post(
            "/api/v1/academic/courses/", {"code": role, "name": role}, format="json"
        )
        assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.regression
def test_course_is_inactivated_instead_of_deleted():
    client = authenticated(User.Role.ADMIN)
    course = client.post(
        "/api/v1/academic/courses/", {"code": "ENF", "name": "Enfermagem"}, format="json"
    ).json()
    assert client.delete(f"/api/v1/academic/courses/{course['id']}/").status_code == 405
    response = client.patch(
        f"/api/v1/academic/courses/{course['id']}/", {"is_active": False}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.django_db
@pytest.mark.integration
def test_professor_creates_room_and_pulls_unassigned_student():
    professor_user, professor, professor_client = create_professor("professor-room")
    _, student, _ = create_student("student-room", "RA-ROOM")
    room_response = professor_client.post(
        "/api/v1/academic/rooms/",
        {"name": "Sala Extensionista", "academic_identifier": "2026.2"},
        format="json",
    )
    assert room_response.status_code == 201
    pulled = professor_client.post(
        f"/api/v1/academic/rooms/{room_response.json()['id']}/pull-student/",
        {"student": str(student.pk)}, format="json",
    )
    assert pulled.status_code == 201
    membership = RoomMembership.objects.get(student=student, is_active=True)
    assert membership.room.responsible_professor == professor
    assert membership.assigned_by == professor_user
    assert AuditEvent.objects.filter(action="ADD_ROOM_STUDENT").exists()


@pytest.mark.django_db
@pytest.mark.security
def test_professor_cannot_inspect_or_change_another_professors_room():
    _, owner, owner_client = create_professor("room-owner")
    _, _, attacker = create_professor("room-attacker")
    room = AcademicRoom.objects.create(name="Sala privada", responsible_professor=owner)
    assert attacker.get(f"/api/v1/academic/rooms/{room.pk}/").status_code == 404
    assert attacker.get(f"/api/v1/academic/rooms/{room.pk}/students/").status_code == 404
    assert (
        attacker.post(
            f"/api/v1/academic/rooms/{room.pk}/close/", {}, format="json"
        ).status_code
        == 404
    )
    assert owner_client.get(f"/api/v1/academic/rooms/{room.pk}/").status_code == 200


@pytest.mark.django_db
@pytest.mark.security
def test_student_search_minimizes_personal_data():
    _, _, professor_client = create_professor("search-professor")
    _, student, _ = create_student("search-student", "RA-SEARCH")
    student.course = Course.objects.create(code="ADS2", name="Tecnologia")
    student.save(update_fields=["course"])
    result = professor_client.get("/api/v1/academic/eligible-students/?q=SEARCH")
    assert result.status_code == 200
    assert len(result.json()) == 1
    assert set(result.json()[0]) == {"id", "name", "ra", "course_name", "active_room"}
    assert "email" not in result.json()[0] and "cpf" not in result.json()[0]


@pytest.mark.django_db
@pytest.mark.integration
def test_transfer_requires_secretariat_and_is_atomic():
    owner_user, owner, _ = create_professor("source-professor")
    _, target, target_client = create_professor("target-professor")
    _, student, _ = create_student("transfer-student", "RA-TRANSFER")
    source = AcademicRoom.objects.create(name="Origem", responsible_professor=owner)
    destination = AcademicRoom.objects.create(name="Destino", responsible_professor=target)
    RoomMembership.objects.create(room=source, student=student, assigned_by=owner_user)
    request = target_client.post(
        f"/api/v1/academic/rooms/{destination.pk}/pull-student/",
        {"student": str(student.pk)}, format="json",
    )
    assert request.status_code == 202
    transfer = RoomTransferRequest.objects.get()
    assert transfer.status == RoomTransferRequest.Status.PENDING
    assert RoomMembership.objects.get(student=student, is_active=True).room == source
    assert target_client.post(
        f"/api/v1/academic/room-transfer-requests/{transfer.pk}/approve/", {}, format="json"
    ).status_code == 403
    secretary, secretary_client = create_actor("secretary-transfer", User.Role.SECRETARIAT)
    approved = secretary_client.post(
        f"/api/v1/academic/room-transfer-requests/{transfer.pk}/approve/",
        {"decision_note": "Transferência confirmada."}, format="json",
    )
    assert approved.status_code == 200
    assert RoomMembership.objects.filter(student=student, is_active=True).count() == 1
    assert RoomMembership.objects.get(student=student, is_active=True).room == destination
    transfer.refresh_from_db()
    assert transfer.decided_by == secretary


@pytest.mark.django_db
@pytest.mark.integration
def test_expertise_normalizes_and_blocks_duplicates():
    _, professor, client = create_professor("expertise-professor")
    first = client.post(
        "/api/v1/academic/my-expertise/",
        {"kind": "COMPETENCY", "text": "  Desenvolvimento   Wéb "}, format="json",
    )
    assert first.status_code == 201
    assert first.json()["normalized_text"] == "desenvolvimento web"
    duplicate = client.post(
        "/api/v1/academic/my-expertise/",
        {"kind": "COMPETENCY", "text": "DESENVOLVIMENTO WEB"}, format="json",
    )
    assert duplicate.status_code == 400
    assert ProfessorExpertise.objects.filter(professor=professor).count() == 1
    assert len(client.get("/api/v1/academic/my-expertise/?q=WÉB").json()) == 1


@pytest.mark.django_db
@pytest.mark.integration
def test_closing_room_deactivates_memberships_and_preserves_history():
    professor_user, professor, client = create_professor("close-professor")
    _, student, _ = create_student("close-student", "RA-CLOSE")
    room = AcademicRoom.objects.create(name="Sala para encerrar", responsible_professor=professor)
    RoomMembership.objects.create(room=room, student=student, assigned_by=professor_user)
    response = client.post(f"/api/v1/academic/rooms/{room.pk}/close/", {}, format="json")
    assert response.status_code == 200
    room.refresh_from_db()
    assert room.status == AcademicRoom.Status.CLOSED and room.closed_at is not None
    membership = RoomMembership.objects.get(student=student)
    assert not membership.is_active and membership.left_at is not None


@pytest.mark.django_db
@pytest.mark.security
def test_closing_room_invalidates_transfer_without_forging_secretariat_decision():
    source_user, source_professor, source_client = create_professor("source-close")
    _, destination_professor, _ = create_professor("destination-close")
    _, student, _ = create_student("student-close-transfer", "RA-CLOSE-TRANSFER")
    source = AcademicRoom.objects.create(name="Origem", responsible_professor=source_professor)
    destination = AcademicRoom.objects.create(
        name="Destino", responsible_professor=destination_professor
    )
    RoomMembership.objects.create(room=source, student=student, assigned_by=source_user)
    transfer = RoomTransferRequest.objects.create(
        student=student, source_room=source, destination_room=destination,
        requesting_professor=destination_professor,
    )
    response = source_client.post(f"/api/v1/academic/rooms/{source.pk}/close/", {}, format="json")
    assert response.status_code == 200
    transfer.refresh_from_db()
    assert transfer.status == RoomTransferRequest.Status.INVALIDATED
    assert transfer.decided_by is None
    assert "origem encerrada" in transfer.decision_note
    assert AuditEvent.objects.filter(
        action="INVALIDATE_ROOM_TRANSFER", object_id=str(transfer.pk)
    ).exists()
