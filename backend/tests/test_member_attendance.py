# ruff: noqa: F811 - fixture importada de test_projects.
import pytest
from projects.grading import group_grade_value
from projects.models import (
    GradeSubmission,
    GroupMember,
    ProjectGroup,
    ShowcaseEntry,
    ShowcaseMemberAttendance,
)

from .test_projects import academic_context  # noqa: F401
from .test_showcase import approved_project, set_evaluator, setup

pytestmark = pytest.mark.django_db
BASE = "/api/v1/projects/showcase/"


@pytest.fixture
def attendance(academic_context):
    offering, _, client, outsider_profile, outsider, _, teacher, secretary, admin, other = setup(
        academic_context
    )
    project = approved_project(client, offering)
    set_evaluator(project["id"], teacher.handler._force_user)
    response = secretary.post(
        BASE,
        {
            "group": project["groups"][0]["id"],
            "date": "2026-12-10T14:00:00Z",
            "location": "Auditório",
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    entry = ShowcaseEntry.objects.get(pk=response.json()["id"])
    second = GroupMember.objects.create(group=entry.group, student=outsider_profile)
    payload = [
        {"member_id": member.pk, "present": member.pk != second.pk}
        for member in entry.group.members.filter(is_active=True)
    ]
    return entry, payload, teacher, client, secretary, admin, other, outsider


def test_partial_attendance_direct_grade_and_retry(attendance):
    entry, payload, teacher, *_ = attendance
    url = f"{BASE}{entry.pk}/member-attendance/"
    response = teacher.post(url, payload, format="json")
    assert response.status_code == 200, response.content
    assert response.json()["status"] == "PRESENTED"
    assert {item["member_id"]: item["present"] for item in response.json()["members"]} == {
        item["member_id"]: item["present"] for item in payload
    }
    assert teacher.post(url, payload, format="json").status_code == 200
    assert ShowcaseMemberAttendance.objects.count() == 2
    changed = [{**item, "present": True} for item in payload]
    assert teacher.post(url, changed, format="json").status_code == 400
    grade_url = f"{BASE}{entry.pk}/evaluation/"
    grade = {"value": "8.75", "observations": "Boa apresentação."}
    response = teacher.post(grade_url, grade, format="json")
    assert response.status_code == 200, response.content
    assert response.json()["evaluation"] == {
        "value": "8.75",
        "observations": "Boa apresentação.",
        "concluded": True,
    }
    assert str(group_grade_value(entry.group)[0]) == "8.75"
    assert teacher.post(grade_url, grade, format="json").status_code == 200
    assert GradeSubmission.objects.count() == 1
    assert teacher.post(grade_url, {**grade, "value": "9"}, format="json").status_code == 400
    detail = teacher.get(f"{BASE}{entry.pk}/").json()
    assert detail["evaluation"]["concluded"] is True


@pytest.mark.parametrize("present", [False, True])
def test_all_absent_or_all_present(attendance, present):
    entry, payload, teacher, *_ = attendance
    response = teacher.post(
        f"{BASE}{entry.pk}/member-attendance/",
        [{**item, "present": present} for item in payload],
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == ("PRESENTED" if present else "ABSENT")
    assert teacher.post(
        f"{BASE}{entry.pk}/evaluation/", {"value": "0"}, format="json"
    ).status_code == (200 if present else 400)


@pytest.mark.parametrize("kind", ["empty", "missing", "duplicate", "foreign", "invalid"])
def test_invalid_roster_rolls_back(attendance, kind):
    entry, payload, teacher, *_ = attendance
    invalid = {
        "empty": [],
        "missing": payload[:1],
        "duplicate": payload + payload[:1],
        "foreign": payload + [{"member_id": 999999, "present": True}],
        "invalid": [{"member_id": payload[0]["member_id"]}],
    }[kind]
    assert (
        teacher.post(f"{BASE}{entry.pk}/member-attendance/", invalid, format="json").status_code
        == 400
    )
    entry.refresh_from_db()
    assert entry.status == "SCHEDULED"
    assert not ShowcaseMemberAttendance.objects.exists()


def test_foreign_existing_membership_rejected(attendance):
    entry, payload, teacher, *_ = attendance
    other = ProjectGroup.objects.create(
        project=entry.group.project, class_offering=entry.group.class_offering
    )
    foreign = GroupMember.objects.create(group=other, student=entry.group.members.first().student)
    assert (
        teacher.post(
            f"{BASE}{entry.pk}/member-attendance/",
            [
                {**payload[0], "member_id": foreign.pk},
                payload[1],
            ],
            format="json",
        ).status_code
        == 400
    )
    assert not ShowcaseMemberAttendance.objects.exists()


def test_only_designated_evaluator(attendance):
    entry, payload, _, *others = attendance
    for client in others:
        assert (
            client.post(f"{BASE}{entry.pk}/member-attendance/", payload, format="json").status_code
            == 403
        )
        assert (
            client.post(f"{BASE}{entry.pk}/evaluation/", {"value": 7}, format="json").status_code
            == 403
        )


@pytest.mark.parametrize("value", ["-1", "10.01", "NaN", "Infinity", "-Infinity", "abc", None])
def test_invalid_grade(attendance, value):
    entry, payload, teacher, *_ = attendance
    teacher.post(f"{BASE}{entry.pk}/member-attendance/", payload, format="json")
    response = teacher.post(f"{BASE}{entry.pk}/evaluation/", {"value": value}, format="json")
    assert response.status_code == 400
    assert not GradeSubmission.objects.exists()


def test_grade_before_attendance_and_cancelled_entry(attendance):
    entry, payload, teacher, *_ = attendance
    assert (
        teacher.post(f"{BASE}{entry.pk}/evaluation/", {"value": 7}, format="json").status_code
        == 400
    )
    entry.status = "CANCELLED"
    entry.save()
    assert (
        teacher.post(f"{BASE}{entry.pk}/member-attendance/", payload, format="json").status_code
        == 400
    )


def test_detail_does_not_expose_members_to_unrelated_user(attendance):
    entry, _, _, client, *_ = attendance
    assert client.get(f"{BASE}{entry.pk}/").status_code == 403


def test_long_group_name_does_not_overflow_project_status_event(attendance):
    entry, payload, teacher, *_ = attendance
    from projects.models import ProjectStateEvent

    entry.group.name = "Grupo de extensão com um nome institucional longo"
    entry.group.save(update_fields=["name"])
    assert (
        teacher.post(f"{BASE}{entry.pk}/member-attendance/", payload, format="json").status_code
        == 200
    )
    assert (
        teacher.post(f"{BASE}{entry.pk}/evaluation/", {"value": "8.75"}, format="json").status_code
        == 200
    )
    event = ProjectStateEvent.objects.get(
        project=entry.group.project, action="EVALUATION_CONCLUDED"
    )
    assert event.new_status == entry.group.project.status
    assert event.previous_status == entry.group.project.status
    assert entry.group.name in event.reason


def test_legacy_presented_can_be_completed_without_changing_aggregate(attendance):
    entry, payload, teacher, *_ = attendance
    entry.status = "PRESENTED"
    entry.save()
    url = f"{BASE}{entry.pk}/member-attendance/"
    assert (
        teacher.post(
            url, [{**item, "present": False} for item in payload], format="json"
        ).status_code
        == 400
    )
    assert not ShowcaseMemberAttendance.objects.exists()
    assert teacher.post(url, payload, format="json").status_code == 200
    assert (
        teacher.post(f"{BASE}{entry.pk}/evaluation/", {"value": "10"}, format="json").status_code
        == 200
    )


def test_rubric_and_direct_evaluations_share_conclusion(attendance):
    from projects.grading import conclude_evaluation, create_rubric, submit_grades
    from projects.models import ProjectForwarding

    entry, payload, teacher, *_ = attendance
    actor = teacher.handler._force_user
    ProjectForwarding.objects.get_or_create(
        project=entry.group.project, defaults={"forwarded_by": actor}
    )
    rubric = create_rubric(actor=actor, title="Rubrica", criteria=[{"name": "Clareza"}])
    teacher.post(f"{BASE}{entry.pk}/member-attendance/", payload, format="json")
    submit_grades(
        actor=actor,
        group=entry.group,
        rubric_id=rubric.pk,
        items=[{"criterion": rubric.criteria.first().pk, "value": "9"}],
    )
    conclude_evaluation(actor=actor, group=entry.group)
    assert (
        teacher.post(f"{BASE}{entry.pk}/evaluation/", {"value": "8"}, format="json").status_code
        == 400
    )
    assert str(group_grade_value(entry.group)[0]) == "9.00"
