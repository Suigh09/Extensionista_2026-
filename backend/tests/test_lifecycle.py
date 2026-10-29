# ruff: noqa: F811 - academic_context e fixture pytest importada de test_projects;
# o parametro homonimo nos testes registra o uso como fixture, nao como redefinicao.
import pytest
from accounts.models import User
from django.db import IntegrityError, transaction
from projects.models import ActiveGroupSlot, GroupInvitation, GroupMember, Project, ProjectTheme
from rest_framework.test import APIClient

from .test_projects import academic_context, create_project  # noqa: F401


def admin_client():
    user = User.objects.create_user(
        username="secretary-lifecycle",
        role="SECRETARIAT",
        password="test-password-123",
    )
    client = APIClient()
    client.force_authenticate(user)
    return client


def command(client, project, action, reason="Justificativa acadêmica registrada"):
    return client.post(
        f"/api/v1/projects/{project['id']}/lifecycle/",
        {"action": action, "reason": reason},
        format="json",
    )


@pytest.mark.django_db
def test_theme_required_visibility_snapshot_and_capacity(academic_context):
    offering, other, student = academic_context
    user, profile, client = student(1)
    _, _, outsider = student(2, other)
    room = profile.room_memberships.get().room
    professor = APIClient()
    professor.force_authenticate(room.responsible_professor.user)
    payload = {"name": "Projeto", "about": "Proposta acadêmica"}
    assert client.post("/api/v1/projects/", payload, format="json").status_code == 400
    theme_data = {
        "room": str(room.pk),
        "title": "Saúde WEB",
        "description": "Criar solução",
        "max_projects": 1,
    }
    assert client.post("/api/v1/projects/themes/", theme_data, format="json").status_code == 403
    response = professor.post("/api/v1/projects/themes/", theme_data, format="json")
    assert response.status_code == 201
    theme = response.json()
    assert outsider.get("/api/v1/projects/themes/").json() == []
    assert (
        outsider.post(
            "/api/v1/projects/",
            {**payload, "theme": theme["id"]},
            format="json",
        ).status_code
        == 400
    )
    created = client.post("/api/v1/projects/", {**payload, "theme": theme["id"]}, format="json")
    assert created.status_code == 201
    assert created.json()["theme_snapshot"]["title"] == "Saúde WEB"
    assert (
        professor.patch(
            f"/api/v1/projects/themes/{theme['id']}/",
            {"title": "Novo título"},
            format="json",
        ).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/projects/{created.json()['id']}/").json()[
            "theme_snapshot"
        ]["title"]
        == "Saúde WEB"
    )
    _, _, second = student(3)
    assert (
        second.post(
            "/api/v1/projects/",
            {**payload, "theme": theme["id"]},
            format="json",
        ).status_code
        == 400
    )
    assert Project.objects.count() == 1


@pytest.mark.django_db
def test_professor_creation_assignment_leader_and_unique_group(academic_context):
    offering, other, student = academic_context
    _, profile, client = student(1)
    _, second, second_client = student(2)
    _, foreign, _ = student(3, other)
    room = profile.room_memberships.get().room
    teacher = APIClient()
    teacher.force_authenticate(room.responsible_professor.user)
    theme = ProjectTheme.objects.create(room=room, title="Tema", description="Orientações")
    payload = {
        "name": "Projeto docente",
        "about": "Proposta",
        "theme": str(theme.pk),
        "leader": profile.pk,
    }
    response = teacher.post("/api/v1/projects/", payload, format="json")
    assert response.status_code == 201
    project = response.json()
    assert project["group"]["leader"] == profile.pk
    path = f"/api/v1/projects/{project['id']}/assign-student/"
    assert client.post(path, {"student_id": second.pk}, format="json").status_code == 403
    assert teacher.post(path, {"student_id": foreign.pk}, format="json").status_code == 400
    assigned = teacher.post(
        path, {"student_id": second.pk, "make_leader": True}, format="json"
    )
    assert assigned.status_code == 200
    assert assigned.json()["group"]["member_count"] == 2
    assert assigned.json()["group"]["leader"] == second.pk
    assert create_project(second_client, offering, approved=False).status_code == 400
    assert ActiveGroupSlot.objects.count() == 2
    # Qualquer integrante ativo pode convidar (decisão do commit 542f8f2).
    _, third, _ = student(4)
    _, fourth, _ = student(5)
    outsider, _, outsider_client = student(6, other)
    invitations_path = f"/api/v1/projects/{project['id']}/invitations/"
    assert outsider_client.post(
        invitations_path, {"invitee": third.pk}, format="json"
    ).status_code == 403
    assert not GroupInvitation.objects.filter(invited_by__user=outsider).exists()
    assert (
        client.post(
            invitations_path,
            {"invitee": third.pk},
            format="json",
        ).status_code
        == 201
    )
    invitation = GroupInvitation.objects.get(group__project_id=project["id"], invitee=third)
    assert invitation.invited_by_id == profile.pk
    assert (
        second_client.post(
            invitations_path,
            {"invitee": fourth.pk},
            format="json",
        ).status_code
        == 201
    )
    _, fifth, _ = student(7)
    assert client.post(
        invitations_path, {"invitee": fifth.pk}, format="json"
    ).status_code == 400
    assert GroupInvitation.objects.filter(group__project_id=project["id"]).count() == 2


@pytest.mark.django_db
@pytest.mark.security
def test_theme_students_requires_active_room_membership(academic_context):
    _, other, student = academic_context
    _, member, member_client = student(1)
    _, _, outsider_client = student(2, other)
    room = member.room_memberships.get().room
    theme = ProjectTheme.objects.create(room=room, title="Consulta", description="Teste")
    path = f"/api/v1/projects/themes/{theme.pk}/students/?q=RA"
    assert outsider_client.get(path).status_code == 403
    assert member_client.get(path).status_code == 200
    member.room_memberships.update(is_active=False)
    assert member_client.get(path).status_code == 403


@pytest.mark.django_db
def test_assign_student_notifies_included_student(academic_context):
    from accounts.models import Notification

    _, profile, _ = academic_context[2](1)
    _, second, _ = academic_context[2](2)
    room = profile.room_memberships.get().room
    teacher = APIClient()
    teacher.force_authenticate(room.responsible_professor.user)
    theme = ProjectTheme.objects.create(room=room, title="Tema", description="Orientações")
    project = teacher.post(
        "/api/v1/projects/",
        {
            "name": "Projeto com notificação",
            "about": "Proposta",
            "theme": str(theme.pk),
            "leader": profile.pk,
        },
        format="json",
    ).json()
    assert (
        teacher.post(
            f"/api/v1/projects/{project['id']}/assign-student/",
            {"student_id": second.pk},
            format="json",
        ).status_code
        == 200
    )
    notice = Notification.objects.get(user=second.user)
    assert notice.kind == Notification.Kind.PROJECT_MEMBER_ADDED
    assert str(notice.project_id) == project["id"]
    assert "incluiu" in notice.body


@pytest.mark.django_db
def test_professor_creation_with_batch_students(academic_context):
    from accounts.models import Notification

    _, profile, _ = academic_context[2](1)
    _, second, _ = academic_context[2](2)
    _, third, _ = academic_context[2](3)
    _, fourth, _ = academic_context[2](4)
    room = profile.room_memberships.get().room
    teacher = APIClient()
    teacher.force_authenticate(room.responsible_professor.user)
    theme = ProjectTheme.objects.create(room=room, title="Tema", description="Orientações")
    created = teacher.post(
        "/api/v1/projects/",
        {
            "name": "Projeto em lote",
            "about": "Proposta",
            "theme": str(theme.pk),
            "leader": profile.pk,
            "student_ids": [second.pk, third.pk, fourth.pk],
        },
        format="json",
    )
    assert created.status_code == 201
    project = created.json()
    assert project["group"]["member_count"] == 4
    assert ActiveGroupSlot.objects.filter(student__in=[second, third, fourth]).count() == 3
    assert (
        Notification.objects.filter(
            kind=Notification.Kind.PROJECT_MEMBER_ADDED,
            user__in=[second.user, third.user, fourth.user],
        ).count()
        == 3
    )
    _, fifth, _ = academic_context[2](5)
    rejected = teacher.post(
        "/api/v1/projects/",
        {
            "name": "Projeto com lote inválido",
            "about": "Proposta",
            "theme": str(theme.pk),
            "leader": fifth.pk,
            "student_ids": [second.pk],
        },
        format="json",
    )
    assert rejected.status_code == 400
    assert not Project.objects.filter(name="Projeto com lote inválido").exists()


@pytest.mark.django_db
def test_pause_resume_blocks_mutations_preserves_conversation_and_history(academic_context):
    offering, _, student = academic_context
    _, _, client = student(1)
    _, colleague, _ = student(2)
    project = create_project(client, offering).json()
    paused = command(client, project, "pause")
    assert paused.status_code == 200
    assert paused.json()["status"] == "PAUSED"
    assert paused.json()["previous_status"] == "APPROVED"
    assert (
        client.patch(
            f"/api/v1/projects/{project['id']}/",
            {"name": "Alterado"},
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/invitations/",
            {"invitee": colleague.pk},
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/follow-ups/",
            {"text": "Mensagem durante pausa"},
            format="json",
        ).status_code
        == 201
    )
    assert create_project(client, offering, approved=False).status_code == 400
    resumed = command(client, project, "resume")
    assert resumed.json()["status"] == "APPROVED"
    assert len(resumed.json()["lifecycle"]) == 3
    assert command(client, project, "resume").status_code == 400


@pytest.mark.django_db
def test_cancel_request_admin_decision_release_and_immutable_history(academic_context):
    offering, _, student = academic_context
    _, profile, client = student(1)
    _, other_profile, other_client = student(2)
    project = create_project(client, offering, approved=False).json()
    admin = admin_client()
    assert command(other_client, project, "request-cancellation").status_code == 404
    assert command(client, project, "cancel").status_code == 403
    assert command(client, project, "request-cancellation", "").status_code == 400
    assert command(client, project, "request-cancellation").status_code == 200
    assert command(client, project, "request-cancellation").status_code == 400
    assert create_project(client, offering, approved=False).status_code == 400
    assert command(admin, project, "decline-cancellation").status_code == 200
    assert ActiveGroupSlot.objects.filter(student=profile).exists()
    assert command(client, project, "request-cancellation").status_code == 200
    cancelled = command(admin, project, "approve-cancellation")
    assert cancelled.json()["status"] == "CANCELLED"
    assert not ActiveGroupSlot.objects.filter(student=profile).exists()
    assert command(admin, project, "resume").status_code == 400
    assert client.get(f"/api/v1/projects/{project['id']}/").status_code == 200
    assert GroupMember.objects.filter(student=profile, group__project_id=project["id"]).exists()
    assert create_project(client, offering, approved=False).status_code == 201
    assert len(client.get("/api/v1/projects/").json()) == 2


@pytest.mark.django_db
def test_database_unique_reservation_and_terminal_invitation(academic_context):
    offering, _, student = academic_context
    _, profile, client = student(1)
    _, colleague, colleague_client = student(2)
    project = create_project(client, offering, approved=False).json()
    invite = client.post(
        f"/api/v1/projects/{project['id']}/invitations/",
        {"invitee": colleague.pk},
        format="json",
    ).json()
    with pytest.raises(IntegrityError), transaction.atomic():
        ActiveGroupSlot.objects.create(student=profile, group_id=project["group"]["id"])
    assert command(admin_client(), project, "cancel").status_code == 200
    assert (
        colleague_client.post(
            f"/api/v1/projects/invitations/{invite['id']}/accept/",
            {},
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/follow-ups/",
            {"text": "Indevido"},
            format="json",
        ).status_code
        == 400
    )
