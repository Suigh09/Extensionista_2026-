import pytest
from academic.models import (
    AcademicRoom,
    ClassOffering,
    Course,
    ProfessorProfile,
    RoomMembership,
    StudentProfile,
    Subject,
)
from accounts.models import AuditEvent
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from projects.models import (
    CollaborationApplication,
    CollaborationOpportunity,
    FollowUpAttachment,
    GroupMember,
    Project,
    ProjectGroup,
    ProjectTheme,
)
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def academic_context(db):
    course = Course.objects.create(code="ADS", name="Análise de Sistemas")
    subject = Subject.objects.create(code="EXT", name="Extensão")
    offering = ClassOffering.objects.create(subject=subject, term="2026.2", code="A")
    other = ClassOffering.objects.create(subject=subject, term="2026.2", code="B")
    rooms = {}

    def student(number, class_offering=offering):
        user = User.objects.create_user(
            username=f"student{number}",
            password="Uma-senha-segura-123",
            role=User.Role.STUDENT,
            first_name=f"Aluno {number}",
        )
        profile = StudentProfile.objects.create(
            user=user,
            ra=f"RA{number}",
            cpf_hash=f"hash-{number:02d}".ljust(64, "x"),
            cpf_last4=f"{number:04d}",
            course=course,
            class_offering=class_offering,
        )
        room = rooms.get(class_offering.pk)
        if not room:
            professor = class_offering.professorprofile_set.filter(user__is_active=True).first()
            if not professor:
                professor_user = User.objects.create_user(
                    username=f"room-professor-{class_offering.code.lower()}",
                    password="Uma-senha-segura-123",
                    role=User.Role.PROFESSOR,
                    first_name=f"Professor {class_offering.code}",
                )
                professor = ProfessorProfile.objects.create(user=professor_user)
            room = AcademicRoom.objects.create(
                name=f"Sala {class_offering.code}", responsible_professor=professor
            )
            rooms[class_offering.pk] = room
        RoomMembership.objects.create(
            room=room,
            student=profile,
            assigned_by=room.responsible_professor.user,
        )
        client = APIClient()
        client.force_authenticate(user)
        return user, profile, client

    return offering, other, student


def create_project(client, offering, approved=True):
    room = AcademicRoom.objects.filter(
        memberships__student__user=client.handler._force_user
    ).first()
    if not room:
        room = AcademicRoom.objects.first()
    theme, _ = ProjectTheme.objects.get_or_create(
        room=room,
        title="Tema de extensão",
        defaults={"description": "Orientações acadêmicas."},
    )
    response = client.post(
        "/api/v1/projects/",
        {
            "name": "Projeto Seguro",
            "about": "Sobre o projeto e seu impacto extensionista.",
            "class_offering": str(offering.pk),
            "theme": str(theme.pk),
        },
        format="json",
    )
    if approved and response.status_code == 201:
        Project.objects.filter(pk=response.json()["id"]).update(status=Project.Status.APPROVED)
    return response


def add_member(owner_client, project_id, profile, invited_client):
    invitation = owner_client.post(
        f"/api/v1/projects/{project_id}/invitations/", {"invitee": profile.pk}, format="json"
    )
    assert invitation.status_code == 201
    accepted = invited_client.post(
        f"/api/v1/projects/invitations/{invitation.json()['id']}/accept/", {}, format="json"
    )
    assert accepted.status_code == 200


@pytest.mark.django_db
@pytest.mark.security
def test_project_patch_cannot_change_institutional_fields(academic_context):
    offering, _, student = academic_context
    _, _, client = student(81)
    project = create_project(client, offering, approved=False).json()
    response = client.patch(
        f"/api/v1/projects/{project['id']}/",
        {"name": "Título permitido", "is_active": False, "status": "ARCHIVED", "origin_room": None},
        format="json",
    )
    assert response.status_code == 200
    stored = Project.objects.get(pk=project["id"])
    assert stored.name == "Título permitido"
    assert stored.is_active is True
    assert stored.status == Project.Status.DRAFT
    assert stored.origin_room_id is not None


@pytest.mark.django_db
@pytest.mark.integration
def test_student_cannot_replace_current_project_even_with_confirmation(academic_context):
    offering, _, student = academic_context
    _, profile, client = student(1)
    first = create_project(client, offering, approved=False).json()
    payload = {
        "name": "Novo projeto vigente",
        "about": "Uma nova proposta acadêmica.",
        "class_offering": str(offering.pk),
        "theme": first["theme"],
    }

    blocked = client.post("/api/v1/projects/", payload, format="json")
    assert blocked.status_code == 400
    assert blocked.json()["code"] == "ACTIVE_PROJECT_CONFLICT"
    assert Project.objects.get(pk=first["id"]).status == Project.Status.DRAFT

    switched = client.post(
        "/api/v1/projects/", {**payload, "replace_active": True}, format="json"
    )
    assert switched.status_code == 400
    assert Project.objects.get(pk=first["id"]).status == Project.Status.DRAFT
    active_memberships = GroupMember.objects.filter(
        student=profile,
        is_active=True,
        group__project__status__in={
            Project.Status.DRAFT,
            Project.Status.PENDING_APPROVAL,
            Project.Status.CHANGES_REQUESTED,
            Project.Status.APPROVED,
        },
    )
    assert active_memberships.count() == 1
    assert str(active_memberships.get().group.project_id) == first["id"]


@pytest.mark.django_db
@pytest.mark.integration
def test_invitation_cannot_bypass_institutional_cancellation(academic_context):
    offering, _, student = academic_context
    _, _, target_owner = student(1)
    _, invitee_profile, invitee = student(2)
    target = create_project(target_owner, offering, approved=False).json()
    current = create_project(invitee, offering, approved=False).json()
    invitation = target_owner.post(
        f"/api/v1/projects/{target['id']}/invitations/",
        {"invitee": invitee_profile.pk},
        format="json",
    ).json()

    blocked = invitee.post(
        f"/api/v1/projects/invitations/{invitation['id']}/accept/", {}, format="json"
    )
    assert blocked.status_code == 400
    assert blocked.json()["code"] == "ACTIVE_PROJECT_CONFLICT"

    accepted = invitee.post(
        f"/api/v1/projects/invitations/{invitation['id']}/accept/",
        {"replace_active": True},
        format="json",
    )
    assert accepted.status_code == 400
    assert Project.objects.get(pk=current["id"]).status == Project.Status.DRAFT
    assert not GroupMember.objects.filter(
        group__project_id=target["id"], student=invitee_profile, is_active=True
    ).exists()


@pytest.mark.django_db
@pytest.mark.integration
def test_student_creates_project_and_initial_group(academic_context):
    offering, _, student = academic_context
    user, profile, client = student(1)
    response = create_project(client, offering, approved=False)
    assert response.status_code == 201
    project = Project.objects.get()
    group = project.groups.get()
    assert GroupMember.objects.filter(group=group, student=profile).exists()
    room = profile.room_memberships.get(is_active=True).room
    assert project.origin_room == room
    assert group.responsible_professor == room.responsible_professor
    assert response.json()["group"]["formation_status"] == "FORMING"
    assert AuditEvent.objects.filter(actor=user, action="CREATE").exists()


@pytest.mark.django_db
@pytest.mark.integration
def test_student_without_active_room_cannot_create_project(academic_context):
    offering, _, student = academic_context
    _, profile, client = student(90)
    membership = profile.room_memberships.get(is_active=True)
    membership.is_active = False
    membership.save(update_fields=["is_active"])
    response = create_project(client, offering, approved=False)
    assert response.status_code == 400
    assert "sala ativa" in str(response.json()).lower()
    assert not Project.objects.exists()


@pytest.mark.django_db
@pytest.mark.integration
def test_project_submission_and_advisor_approval(academic_context):
    offering, _, student = academic_context
    professor_user = User.objects.create_user(
        username="advisor", password="Uma-senha-segura-123", role=User.Role.PROFESSOR
    )
    professor = ProfessorProfile.objects.create(user=professor_user)
    professor.class_offerings.add(offering)
    _, _, student_client = student(1)
    _, colleague_profile, colleague_client = student(2)
    project = create_project(student_client, offering, approved=False).json()
    assert project["status"] == "DRAFT"
    add_member(student_client, project["id"], colleague_profile, colleague_client)
    submitted = student_client.post(f"/api/v1/projects/{project['id']}/submit/", {}, format="json")
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "PENDING_APPROVAL"
    professor_client = APIClient()
    professor_client.force_authenticate(professor_user)
    approved = professor_client.post(
        f"/api/v1/projects/{project['id']}/approve/",
        {"feedback": "Proposta adequada."},
        format="json",
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"


@pytest.mark.django_db
@pytest.mark.integration
def test_golden_flow_interdisciplinary_partnership(academic_context):
    offering, other, student = academic_context
    publisher_user, _, publisher = student(1, offering)
    _, publisher_colleague, publisher_colleague_client = student(2, offering)
    publisher_project = create_project(publisher, offering).json()
    add_member(publisher, publisher_project["id"], publisher_colleague, publisher_colleague_client)

    candidate_user, _, candidate = student(3, other)
    _, candidate_colleague, candidate_colleague_client = student(4, other)
    candidate_project = create_project(candidate, other).json()
    add_member(candidate, candidate_project["id"], candidate_colleague, candidate_colleague_client)
    assert (
        candidate.post(
            f"/api/v1/projects/{candidate_project['id']}/follow-ups/",
            {"text": "Histórico do grupo candidato", "kind": "PROGRESS"},
            format="json",
        ).status_code
        == 201
    )

    opportunity = publisher.post(
        "/api/v1/projects/collaborations/opportunities/",
        {
            "group": publisher_project["group"]["id"],
            "title": "Precisamos de apoio em experiência do usuário",
            "description": "Buscamos outro grupo para validar a solução com a comunidade.",
            "desired_skills": ["UX", "pesquisa"],
        },
        format="json",
    )
    assert opportunity.status_code == 201
    assert opportunity.json()["status"] == "OPEN"

    application = candidate.post(
        f"/api/v1/projects/collaborations/opportunities/{opportunity.json()['id']}/applications/",
        {
            "candidate_group": candidate_project["group"]["id"],
            "message": "Nosso grupo pode conduzir entrevistas e testes.",
        },
        format="json",
    )
    assert application.status_code == 201
    accepted = publisher.post(
        f"/api/v1/projects/collaborations/applications/{application.json()['id']}/accept/",
        {},
        format="json",
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ACCEPTED"

    target = Project.objects.get(pk=publisher_project["id"])
    assert target.groups.filter(is_active=True).count() == 2
    assert not Project.objects.get(pk=candidate_project["id"]).is_active
    assert CollaborationOpportunity.objects.get().status == "MATCHED"
    assert CollaborationApplication.objects.get().status == "ACCEPTED"
    assert publisher.get(f"/api/v1/projects/{target.pk}/").status_code == 200
    assert candidate.get(f"/api/v1/projects/{target.pk}/").status_code == 200
    timeline = candidate.get(f"/api/v1/projects/{target.pk}/timeline/").json()
    assert any(item["description"] == "Histórico do grupo candidato" for item in timeline)
    professor_user = User.objects.create_user(
        username="professor-interdisciplinar",
        password="Uma-senha-segura-123",
        role=User.Role.PROFESSOR,
    )
    professor = ProfessorProfile.objects.create(user=professor_user)
    professor.class_offerings.add(other)
    target.groups.filter(class_offering=other).update(evaluator=professor)
    professor_client = APIClient()
    professor_client.force_authenticate(professor_user)
    assert any(
        item["id"] == str(target.pk)
        for item in professor_client.get("/api/v1/projects/available-to-professor/").json()
    )
    assert AuditEvent.objects.filter(
        actor=publisher_user, action="CREATE_COLLABORATION_OPPORTUNITY"
    ).exists()
    assert AuditEvent.objects.filter(actor=candidate_user, action="APPLY_COLLABORATION").exists()


@pytest.mark.django_db
@pytest.mark.security
def test_collaboration_enforces_formed_groups_ownership_and_two_group_limit(academic_context):
    offering, other, student = academic_context
    _, _, publisher = student(1, offering)
    publisher_project = create_project(publisher, offering).json()
    unformed = publisher.post(
        "/api/v1/projects/collaborations/opportunities/",
        {
            "group": publisher_project["group"]["id"],
            "title": "Apoio",
            "description": "Precisamos de colaboração.",
            "desired_skills": [],
        },
        format="json",
    )
    assert unformed.status_code == 400

    _, publisher_colleague, publisher_colleague_client = student(2, offering)
    add_member(publisher, publisher_project["id"], publisher_colleague, publisher_colleague_client)
    opportunity = publisher.post(
        "/api/v1/projects/collaborations/opportunities/",
        {
            "group": publisher_project["group"]["id"],
            "title": "Apoio",
            "description": "Precisamos de colaboração.",
            "desired_skills": [],
        },
        format="json",
    ).json()
    assert (
        publisher.post(
            f"/api/v1/projects/collaborations/opportunities/{opportunity['id']}/applications/",
            {"candidate_group": publisher_project["group"]["id"], "message": "Próprio grupo"},
            format="json",
        ).status_code
        == 400
    )

    _, _, candidate = student(3, other)
    candidate_project = create_project(candidate, other).json()
    assert (
        candidate.post(
            f"/api/v1/projects/collaborations/opportunities/{opportunity['id']}/applications/",
            {"candidate_group": candidate_project["group"]["id"], "message": "Ainda incompleto"},
            format="json",
        ).status_code
        == 400
    )
    _, candidate_colleague, candidate_colleague_client = student(4, other)
    add_member(candidate, candidate_project["id"], candidate_colleague, candidate_colleague_client)
    application = candidate.post(
        f"/api/v1/projects/collaborations/opportunities/{opportunity['id']}/applications/",
        {"candidate_group": candidate_project["group"]["id"], "message": "Grupo formado"},
        format="json",
    ).json()
    _, _, outsider = student(9, other)
    assert (
            outsider.post(
                f"/api/v1/projects/collaborations/applications/{application['id']}/accept/",
            {},
            format="json",
        ).status_code
            == 403
    )
    assert (
        outsider.post(
            f"/api/v1/projects/collaborations/applications/{application['id']}/cancel/",
            {},
            format="json",
        ).status_code
        == 403
    )


@pytest.mark.django_db
@pytest.mark.security
def test_project_requires_student_from_selected_class(academic_context):
    offering, other, student = academic_context
    _, _, client = student(1)
    assert create_project(client, other).status_code == 400
    admin = User.objects.create_user(username="admin-project", password="x", role=User.Role.ADMIN)
    admin_client = APIClient()
    admin_client.force_authenticate(admin)
    assert create_project(admin_client, offering).status_code == 400


@pytest.mark.django_db
@pytest.mark.api
def test_golden_flow_forms_group_with_four_students(academic_context):
    offering, _, student = academic_context
    _, creator_profile, creator = student(1)
    project_id = create_project(creator, offering).json()["id"]
    members = [student(number) for number in (2, 3, 4)]
    for _, profile, invited_client in members:
        invitation = creator.post(
            f"/api/v1/projects/{project_id}/invitations/",
            {"invitee": profile.pk},
            format="json",
        )
        assert invitation.status_code == 201
        accepted = invited_client.post(
            f"/api/v1/projects/invitations/{invitation.json()['id']}/accept/", {}, format="json"
        )
        assert accepted.status_code == 200
    detail = creator.get(f"/api/v1/projects/{project_id}/")
    assert detail.json()["group"]["member_count"] == 4
    assert detail.json()["group"]["formation_status"] == "COMPLETE"
    assert detail.json()["group"]["members"][0].keys() >= {"name", "ra"}
    assert "cpf" not in str(detail.json()).lower()


@pytest.mark.django_db
@pytest.mark.security
def test_duplicate_ineligible_third_party_and_fifth_member_are_blocked(academic_context):
    offering, other, student = academic_context
    _, _, creator = student(1)
    project_id = create_project(creator, offering).json()["id"]
    _, eligible, invited = student(2)
    invitation = creator.post(
        f"/api/v1/projects/{project_id}/invitations/", {"invitee": eligible.pk}, format="json"
    )
    assert invitation.status_code == 201
    assert (
        creator.post(
            f"/api/v1/projects/{project_id}/invitations/", {"invitee": eligible.pk}, format="json"
        ).status_code
        == 400
    )
    _, outsider, outsider_client = student(9, other)
    outsider.course = Course.objects.create(code="ENG", name="Engenharia")
    outsider.save(update_fields=["course"])
    assert (
        creator.post(
            f"/api/v1/projects/{project_id}/invitations/", {"invitee": outsider.pk}, format="json"
        ).status_code
        == 400
    )
    assert (
        outsider_client.post(
            f"/api/v1/projects/invitations/{invitation.json()['id']}/accept/", {}, format="json"
        ).status_code
        == 403
    )
    assert (
        invited.post(
            f"/api/v1/projects/invitations/{invitation.json()['id']}/accept/", {}, format="json"
        ).status_code
        == 200
    )
    for number in (3, 4):
        _, profile, client = student(number)
        invite = creator.post(
            f"/api/v1/projects/{project_id}/invitations/", {"invitee": profile.pk}, format="json"
        ).json()
        assert (
            client.post(
                f"/api/v1/projects/invitations/{invite['id']}/accept/", {}, format="json"
            ).status_code
            == 200
        )
    _, fifth, _ = student(5)
    assert (
        creator.post(
            f"/api/v1/projects/{project_id}/invitations/", {"invitee": fifth.pk}, format="json"
        ).status_code
        == 400
    )


@pytest.mark.django_db
@pytest.mark.regression
def test_invitee_declines_and_member_cancels_pending_invitation(academic_context):
    offering, _, student = academic_context
    _, _, creator = student(1)
    project_id = create_project(creator, offering).json()["id"]
    _, profile2, invited2 = student(2)
    invitation2 = creator.post(
        f"/api/v1/projects/{project_id}/invitations/", {"invitee": profile2.pk}, format="json"
    ).json()
    assert (
        invited2.post(
            f"/api/v1/projects/invitations/{invitation2['id']}/decline/", {}, format="json"
        ).json()["status"]
        == "DECLINED"
    )
    _, profile3, _ = student(3)
    invitation3 = creator.post(
        f"/api/v1/projects/{project_id}/invitations/", {"invitee": profile3.pk}, format="json"
    ).json()
    assert (
        creator.post(
            f"/api/v1/projects/invitations/{invitation3['id']}/cancel/", {}, format="json"
        ).json()["status"]
        == "CANCELLED"
    )


@pytest.mark.django_db
@pytest.mark.security
def test_student_cannot_read_or_edit_another_project(academic_context):
    offering, _, student = academic_context
    _, _, owner = student(1)
    project_id = create_project(owner, offering).json()["id"]
    _, _, stranger = student(2)
    assert stranger.get(f"/api/v1/projects/{project_id}/").status_code == 404
    assert (
        stranger.patch(
            f"/api/v1/projects/{project_id}/", {"name": "Ataque"}, format="json"
        ).status_code
        == 404
    )
    assert stranger.get(f"/api/v1/projects/{project_id}/invitations/").status_code == 403


@pytest.mark.django_db
@pytest.mark.api
def test_eligible_search_exposes_only_minimum_data(academic_context):
    _, _, student = academic_context
    _, _, client = student(1)
    student(2)
    response = client.get("/api/v1/projects/eligible-students/?q=RA2")
    assert response.status_code == 200
    assert set(response.json()[0]) == {
        "id", "user", "name", "ra", "course_name", "class_code", "term"
    }
    assert "cpf" not in str(response.json()).lower()


@pytest.mark.django_db
@pytest.mark.security
def test_pending_invitations_reserve_the_three_available_group_slots(academic_context):
    offering, _, student = academic_context
    _, _, creator = student(1)
    project_id = create_project(creator, offering).json()["id"]
    for number in (2, 3, 4):
        _, profile, _ = student(number)
        response = creator.post(
            f"/api/v1/projects/{project_id}/invitations/", {"invitee": profile.pk}, format="json"
        )
        assert response.status_code == 201
    _, fifth, _ = student(5)
    blocked = creator.post(
        f"/api/v1/projects/{project_id}/invitations/", {"invitee": fifth.pk}, format="json"
    )
    assert blocked.status_code == 400
    assert "convites pendentes" in str(blocked.json()).lower()


@pytest.mark.django_db
@pytest.mark.api
def test_eligible_search_requires_two_characters_and_uses_same_active_room(academic_context):
    offering, other, student = academic_context
    _, _, client = student(1)
    student(2, other)
    student(4, offering)
    _, different_course, _ = student(3, other)
    different_course.course = Course.objects.create(code="DIR", name="Direito")
    different_course.save(update_fields=["course"])
    assert client.get("/api/v1/projects/eligible-students/?q=A").json() == []
    result = client.get("/api/v1/projects/eligible-students/?q=Aluno").json()
    assert [item["name"] for item in result] == ["Aluno 4"]


@pytest.mark.django_db
@pytest.mark.api
def test_follow_ups_are_free_independent_and_visible_in_timeline(academic_context):
    offering, _, student = academic_context
    student_user, _, student_client = student(1)
    project_id = create_project(student_client, offering).json()["id"]
    professor_user = User.objects.create_user(
        username="professor-followup",
        password="Uma-senha-segura-123",
        role=User.Role.PROFESSOR,
        first_name="Professora",
    )
    professor = ProfessorProfile.objects.create(user=professor_user)
    professor.class_offerings.add(offering)
    ProjectGroup.objects.filter(project_id=project_id).update(responsible_professor=professor)
    professor_client = APIClient()
    professor_client.force_authenticate(professor_user)
    for number in range(5):
        response = student_client.post(
            f"/api/v1/projects/{project_id}/follow-ups/",
            {"text": f"Atualização livre {number + 1}", "kind": "PROGRESS"},
            format="json",
        )
        assert response.status_code == 201
    assert (
        professor_client.post(
            f"/api/v1/projects/{project_id}/follow-ups/",
            {"text": "Observação da professora", "kind": "OBSERVATION"},
            format="json",
        ).status_code
        == 201
    )
    timeline = student_client.get(f"/api/v1/projects/{project_id}/timeline/")
    assert timeline.status_code == 200
    assert len(timeline.json()) == 6
    assert all(item["event_type"] == "FOLLOW_UP" for item in timeline.json())
    assert AuditEvent.objects.filter(actor=student_user, action="FOLLOW_UP").count() == 5


@pytest.mark.django_db
@pytest.mark.security
def test_publication_sanitizes_rich_text_and_protects_attachment_download(
    academic_context, tmp_path
):
    offering, other, student = academic_context
    _, _, owner = student(1)
    project_id = create_project(owner, offering).json()["id"]
    upload = SimpleUploadedFile("evidencia.pdf", b"%PDF-1.4 test", content_type="application/pdf")
    with override_settings(MEDIA_ROOT=tmp_path):
        response = owner.post(
            f"/api/v1/projects/{project_id}/follow-ups/",
            {
                "text": '<p><strong>Entrega</strong><script>alert(1)</script></p>',
                "attachments": upload,
            },
            format="multipart",
        )
        assert response.status_code == 201
        assert "<strong>Entrega</strong>" in response.json()["text"]
        assert "<script" not in response.json()["text"]
        attachment = response.json()["attachments"][0]
        assert FollowUpAttachment.objects.count() == 1
        assert owner.get(f"/api/v1{attachment['download_url']}").status_code == 200
        _, _, outsider = student(9, other)
        assert outsider.get(f"/api/v1{attachment['download_url']}").status_code == 404


@pytest.mark.django_db
@pytest.mark.security
def test_publication_rejects_executable_and_double_extension(academic_context, tmp_path):
    offering, _, student = academic_context
    _, _, owner = student(1)
    project_id = create_project(owner, offering).json()["id"]
    dangerous = SimpleUploadedFile(
        "relatorio.pdf.exe", b"MZ", content_type="application/x-msdownload"
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        response = owner.post(
            f"/api/v1/projects/{project_id}/follow-ups/",
            {"text": "Arquivo", "attachments": dangerous},
            format="multipart",
        )
    assert response.status_code == 400
    assert FollowUpAttachment.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.security
def test_publication_rejects_arbitrary_zip_renamed_as_office_document(academic_context, tmp_path):
    offering, _, student = academic_context
    _, _, owner = student(1)
    project_id = create_project(owner, offering).json()["id"]
    disguised = SimpleUploadedFile(
        "relatorio.docx",
        b"PK\x03\x04not-a-valid-ooxml-package",
        content_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        response = owner.post(
            f"/api/v1/projects/{project_id}/follow-ups/",
            {"text": "Arquivo", "attachments": disguised}, format="multipart",
        )
    assert response.status_code == 400
    assert "estrutura interna" in str(response.json()).lower()
    assert FollowUpAttachment.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.security
def test_follow_up_blocks_user_without_project_access(academic_context):
    offering, other, student = academic_context
    _, _, owner = student(1)
    project_id = create_project(owner, offering).json()["id"]
    _, _, outsider = student(9, other)
    assert outsider.get(f"/api/v1/projects/{project_id}/follow-ups/").status_code == 404
    assert (
            outsider.post(
                f"/api/v1/projects/{project_id}/follow-ups/", {"text": "Intrusão"}, format="json"
            ).status_code
            == 404
    )


@pytest.mark.django_db
@pytest.mark.integration
def test_professor_creates_configurable_milestone_for_class(academic_context):
    offering, other, student = academic_context
    _, _, first = student(1)
    _, _, second = student(2)
    first_project = create_project(first, offering).json()["id"]
    second_project = create_project(second, offering).json()["id"]
    professor_user = User.objects.create_user(
        username="professor-marco", password="Uma-senha-segura-123", role=User.Role.PROFESSOR
    )
    professor = ProfessorProfile.objects.create(user=professor_user)
    professor.class_offerings.add(offering)
    client = APIClient()
    client.force_authenticate(professor_user)
    response = client.post(
        "/api/v1/projects/milestones/",
        {
            "title": "Protótipo navegável",
            "description": "Demonstrar o fluxo principal",
            "due_at": "2026-09-30T18:00:00-03:00",
            "scope": "CLASS",
            "class_offering": str(offering.pk),
            "requires_delivery": True,
            "requires_approval": False,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["project_count"] == 2
    for project_id in (first_project, second_project):
        milestones = first.get(f"/api/v1/projects/{project_id}/milestones/")
        if project_id == second_project:
            milestones = second.get(f"/api/v1/projects/{project_id}/milestones/")
        assert milestones.status_code == 200
        assert milestones.json()[0]["title"] == "Protótipo navegável"
    denied = client.post(
        "/api/v1/projects/milestones/",
        {
            "title": "Turma indevida",
            "due_at": "2026-10-01T18:00:00-03:00",
            "scope": "CLASS",
            "class_offering": str(other.pk),
        },
        format="json",
    )
    assert denied.status_code == 403
