# ruff: noqa: F811
import pytest
from academic.models import ProfessorExpertise, ProfessorProfile
from accounts.models import Notification, User
from projects.models import (
    EvaluatorAssignment,
    GradeSubmission,
    Project,
    ProjectForwarding,
    ProjectGroup,
    Rubric,
    ShowcaseEntry,
    ShowcaseRoom,
)

from .test_planning import BASE, planning  # noqa: F401
from .test_projects import academic_context  # noqa: F401


@pytest.fixture
def allocation(planning):
    student, teacher, secretary, admin, project, building, payload = planning
    forwarding = project.forwarding
    forwarding.required_competencies = "Extensão"
    forwarding.save(update_fields=["required_competencies"])
    candidates = []
    for name in ("Ana", "Bia"):
        user = User.objects.create_user(
            username=f"evaluator-{name}", first_name=name, role="PROFESSOR"
        )
        professor = ProfessorProfile.objects.create(user=user)
        ProfessorExpertise.objects.create(professor=professor, kind="COMPETENCY", text="Extensão")
        candidates.append(professor)
    group = project.groups.first()
    assert secretary.post(BASE + "showcase-planning/", payload, format="json").status_code == 200
    other_project = Project.objects.create(
        name="Outro projeto",
        about="Teste",
        status="APPROVED",
        created_by=project.created_by,
        class_offering=project.class_offering,
    )
    ProjectForwarding.objects.create(
        project=other_project,
        forwarded_by=teacher.handler._force_user,
        required_competencies="Extensão",
    )
    other_group = ProjectGroup.objects.create(
        project=other_project,
        class_offering=project.class_offering,
        responsible_professor=group.responsible_professor,
    )
    other_room = ShowcaseRoom.objects.create(building_id=building, number=2, name="Sala 2")
    other_payload = {**payload, "group": str(other_group.pk), "room": str(other_room.pk)}
    return planning, candidates, group, other_group, other_payload


def designate(secretary, group, professor):
    return secretary.post(
        BASE + f"groups/{group.pk}/designate-evaluator/",
        {
            "professor": str(professor.pk),
            "justification": "Escolha manual justificada.",
        },
        format="json",
    )


def auto(secretary, payload):
    return secretary.post(
        BASE + "showcase-planning/allocate-evaluators/",
        {
            "day": payload["day"],
            "room": payload["room"],
        },
        format="json",
    )


@pytest.mark.django_db
def test_manual_options_single_evaluator_history_notification(allocation):
    planning, candidates, group, _, _ = allocation
    student, teacher, secretary, _, project, _, _ = planning
    url = BASE + f"groups/{group.pk}/evaluator-options/"
    assert student.get(url).status_code == 403
    assert teacher.get(url).status_code == 403
    options = secretary.get(url).json()
    assert options["current"] is None
    assert str(group.responsible_professor_id) not in [
        item["professor_profile_id"] for item in options["recommendations"]
    ]
    response = designate(secretary, group, candidates[0])
    assert response.status_code == 201
    group.refresh_from_db()
    assert group.evaluator_id == candidates[0].pk
    assert EvaluatorAssignment.objects.filter(group=group).count() == 1
    assert Notification.objects.filter(
        user=candidates[0].user, kind="EVALUATOR_DESIGNATED"
    ).exists()
    agenda = secretary.get(BASE + "showcase-planning/").json()
    assert agenda["entries"][0]["evaluator_name"] == "Ana"
    assert agenda["entries"][0]["evaluator_id"] == str(candidates[0].pk)
    assert project.groups.count() == 1


@pytest.mark.django_db
def test_manual_conflict_between_rooms_and_adjacent_slots(allocation):
    planning, candidates, group, other, payload = allocation
    _, _, secretary, _, _, _, _ = planning
    assert secretary.post(BASE + "showcase-planning/", payload, format="json").status_code == 200
    assert designate(secretary, group, candidates[0]).status_code == 201
    options = secretary.get(BASE + f"groups/{other.pk}/evaluator-options/").json()
    ana = next(item for item in options["recommendations"] if item["name"] == "Ana")
    assert not ana["available"]
    assert designate(secretary, other, candidates[0]).status_code == 400
    entry = other.showcase_entry
    moved = secretary.post(
        BASE + "showcase-planning/",
        {
            **payload,
            "start_time": "09:30",
            "end_time": "10:00",
            "expected_updated_at": entry.updated_at.isoformat(),
        },
        format="json",
    )
    assert moved.status_code == 200
    assert designate(secretary, other, candidates[0]).status_code == 201
    group_entry = ShowcaseEntry.objects.get(group=group)
    blocked_resize = secretary.post(
        BASE + "showcase-planning/",
        {
            **planning[-1],
            "end_time": "10:00",
            "expected_updated_at": group_entry.updated_at.isoformat(),
        },
        format="json",
    )
    assert blocked_resize.status_code == 400
    group_entry.refresh_from_db()
    assert (group_entry.end_date - group_entry.date).total_seconds() == 1800


@pytest.mark.django_db
def test_auto_balances_load_is_idempotent_and_preserves_manual(allocation):
    planning, candidates, group, other, payload = allocation
    _, _, secretary, _, _, _, original = planning
    same_room = {**payload, "room": original["room"], "start_time": "09:30", "end_time": "10:00"}
    secretary.post(BASE + "showcase-planning/", same_room, format="json")
    result = auto(secretary, original)
    assert result.status_code == 200
    assert len(result.json()["allocated"]) == 2
    group.refresh_from_db()
    other.refresh_from_db()
    assert {group.evaluator_id, other.evaluator_id} == {p.pk for p in candidates}
    assert EvaluatorAssignment.objects.count() == 2
    again = auto(secretary, original).json()
    assert len(again["preserved"]) == 2 and again["allocated"] == []
    assert EvaluatorAssignment.objects.count() == 2


@pytest.mark.django_db
def test_auto_never_replaces_manual_choice(allocation):
    planning, candidates, group, _, _ = allocation
    _, _, secretary, _, _, _, payload = planning
    assert designate(secretary, group, candidates[1]).status_code == 201
    result = auto(secretary, payload).json()
    assert result["allocated"] == [] and result["preserved"] == [str(group.pk)]
    group.refresh_from_db()
    assert group.evaluator_id == candidates[1].pk


@pytest.mark.django_db
def test_auto_reports_no_compatible_or_available_candidate(allocation):
    planning, candidates, group, other, payload = allocation
    _, _, secretary, _, _, _, original = planning
    secretary.post(BASE + "showcase-planning/", payload, format="json")
    designate(secretary, group, candidates[0])
    ProfessorExpertise.objects.filter(professor=candidates[1]).delete()
    result = auto(secretary, payload).json()
    assert result["allocated"] == []
    assert result["pending"][0]["group"] == str(other.pk)
    assert "Escolha manualmente" in result["pending"][0]["reason"]
    ProfessorExpertise.objects.all().delete()
    ShowcaseEntry.objects.filter(group=group).update(status="CANCELLED")
    result = auto(secretary, payload).json()
    assert len(result["pending"]) == 1
    assert auto(secretary, original).json()["pending"] == []


@pytest.mark.django_db
@pytest.mark.parametrize("record", ["presence", "grades"])
def test_cannot_replace_after_presence_or_grades(allocation, record):
    planning, candidates, group, _, _ = allocation
    _, teacher, secretary, _, _, _, payload = planning
    if record == "presence":
        ShowcaseEntry.objects.filter(group=group).update(status="PRESENTED")
    else:
        rubric = Rubric.objects.create(
            owner=teacher.handler._force_user.professor_profile, title="Teste"
        )
        GradeSubmission.objects.create(
            group=group, rubric=rubric, author=teacher.handler._force_user
        )
    assert designate(secretary, group, candidates[0]).status_code == 400
    assert secretary.get(BASE + f"groups/{group.pk}/evaluator-options/").json()["locked"]
    assert not auto(secretary, payload).json()["allocated"]


@pytest.mark.django_db
def test_auto_permissions_and_inactive_professor(allocation):
    planning, candidates, group, _, _ = allocation
    student, teacher, secretary, admin, _, _, payload = planning
    assert auto(student, payload).status_code == 403
    assert auto(teacher, payload).status_code == 403
    candidates[0].user.is_active = False
    candidates[0].user.save(update_fields=["is_active"])
    assert designate(secretary, group, candidates[0]).status_code == 400
    assert auto(admin, payload).status_code == 200
    group.refresh_from_db()
    assert group.evaluator_id == candidates[1].pk


@pytest.mark.django_db
def test_legacy_schedule_endpoint_cannot_double_book_evaluator(allocation):
    planning, candidates, group, other, _ = allocation
    _, _, secretary, _, _, _, _ = planning
    assert designate(secretary, group, candidates[0]).status_code == 201
    # Designation before a schedule is allowed, but the later schedule must check availability.
    assert designate(secretary, other, candidates[0]).status_code == 201
    response = secretary.post(
        BASE + "showcase/",
        {
            "group": str(other.pk),
            "date": group.showcase_entry.date.isoformat(),
            "location": "Legado",
        },
        format="json",
    )
    assert response.status_code == 400
    assert not ShowcaseEntry.objects.filter(group=other).exists()


@pytest.mark.django_db
def test_invalid_professor_id_is_validation_error(allocation):
    planning, _, group, _, _ = allocation
    secretary = planning[2]
    response = secretary.post(
        BASE + f"groups/{group.pk}/designate-evaluator/",
        {
            "professor": "not-a-profile-id",
            "justification": "Teste",
        },
        format="json",
    )
    assert response.status_code == 400
