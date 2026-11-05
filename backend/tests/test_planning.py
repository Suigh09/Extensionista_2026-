# ruff: noqa: F811
from datetime import datetime
from importlib import import_module
from types import SimpleNamespace

import pytest
from accounts.models import Notification
from django.apps import apps
from django.db import connection
from django.utils import timezone
from projects.models import Project, ProjectForwarding, ProjectGroup, ShowcaseEntry
from projects.planning import building_code
from rest_framework.test import APIClient

from .test_projects import academic_context  # noqa: F401
from .test_showcase import approved_project, setup

BASE = "/api/v1/projects/"


@pytest.fixture
def planning(academic_context):
    _, _, student, _, _, _, teacher, secretary, admin, _ = setup(academic_context)
    project = approved_project(student, academic_context[0])
    instance = Project.objects.get(pk=project["id"])
    ProjectForwarding.objects.create(project=instance, forwarded_by=teacher.handler._force_user)
    building = admin.post(BASE + "showcase-buildings/", {}, format="json").json()["id"]
    room = admin.post(BASE + f"showcase-buildings/{building}/rooms/", {}, format="json").json()[
        "id"
    ]
    day = secretary.post(
        BASE + "showcase-days/",
        {
            "date": "2026-12-10",
            "start_time": "08:00",
            "end_time": "18:00",
        },
        format="json",
    ).json()["id"]
    payload = {
        "group": project["groups"][0]["id"],
        "day": day,
        "room": room,
        "start_time": "09:00",
        "end_time": "09:30",
    }
    return student, teacher, secretary, admin, instance, building, payload


@pytest.mark.django_db
def test_venues_staff_only_auto_numbers_and_rename(planning):
    student, teacher, secretary, admin, _, building, _ = planning
    for client in (student, teacher):
        assert client.post(BASE + "showcase-buildings/", {}, format="json").status_code == 403
        assert client.post(BASE + f"showcase-buildings/{building}/rooms/", {}).status_code == 403
        assert (
            client.patch(BASE + f"showcase-buildings/{building}/", {"name": "X"}).status_code == 403
        )
    assert (
        admin.patch(
            BASE + f"showcase-buildings/{building}/",
            {
                "name": "Anfiteatro",
            },
            format="json",
        ).status_code
        == 200
    )
    assert secretary.post(BASE + "showcase-buildings/", {}, format="json").status_code == 201
    new_room = secretary.post(BASE + f"showcase-buildings/{building}/rooms/", {}, format="json")
    assert new_room.status_code == 201
    assert secretary.patch(
        BASE + f"showcase-buildings/{building}/", {"name": "Anfiteatro"}, format="json"
    ).status_code == 200
    assert secretary.patch(
        BASE + f"showcase-rooms/{new_room.json()['id']}/", {"name": "Auditório"}, format="json"
    ).status_code == 200
    data = secretary.get(BASE + "showcase-planning/").json()
    assert [(b["code"], b["name"]) for b in data["buildings"]] == [
        ("A", "Anfiteatro"),
        ("B", "Prédio B"),
    ]
    assert [r["number"] for r in data["rooms"]] == [1, 2]
    assert building_code(26) == "Z"
    assert building_code(27) == "AA"


@pytest.mark.django_db
def test_schedule_move_resize_cancel_and_presence_same_entry(planning):
    student, teacher, secretary, _, project, _, payload = planning
    group = project.groups.first()
    group.evaluator = teacher.handler._force_user.professor_profile
    group.save(update_fields=["evaluator"])
    assert student.post(BASE + "showcase-planning/", payload, format="json").status_code == 403
    assert teacher.get(BASE + "showcase-planning/").status_code == 403
    response = secretary.post(BASE + "showcase-planning/", payload, format="json")
    assert response.status_code == 200, response.content
    entry_id = response.json()["id"]
    version = response.json()["updated_at"]
    assert secretary.post(BASE + "showcase-planning/", payload, format="json").status_code == 400
    response = secretary.post(
        BASE + "showcase-planning/",
        {
            **payload,
            "start_time": "10:00",
            "end_time": "11:00",
            "expected_updated_at": version,
        },
        format="json",
    )
    assert response.status_code == 200
    entry = ShowcaseEntry.objects.get(pk=entry_id)
    assert timezone.localtime(entry.date).hour == 10
    assert (entry.end_date - entry.date).total_seconds() == 3600
    assert teacher.get(BASE + "showcase/").json()[0]["id"] == entry_id
    response = teacher.post(BASE + f"showcase/{entry_id}/", {"status": "PRESENTED"}, format="json")
    assert response.status_code == 200
    response = secretary.post(
        BASE + "showcase-planning/",
        {
            **payload,
            "expected_updated_at": response.json()["updated_at"],
        },
        format="json",
    )
    assert response.status_code == 400
    assert ShowcaseEntry.objects.filter(group=group).count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "overrides",
    [
        {"start_time": "09:15"},
        {"end_time": "09:00"},
        {"end_time": "19:00"},
        {"start_time": "07:30"},
        {"start_time": "09:00:01"},
        {"room": "00000000-0000-0000-0000-000000000000"},
    ],
)
def test_invalid_schedule_rejected(planning, overrides):
    _, _, secretary, _, _, _, payload = planning
    assert secretary.post(
        BASE + "showcase-planning/",
        {
            **payload,
            **overrides,
        },
        format="json",
    ).status_code in {400, 404}
    assert ShowcaseEntry.objects.count() == 0


@pytest.mark.django_db
def test_room_allows_multiple_groups_same_slot(planning):
    _, _, secretary, _, project, _, payload = planning
    group2 = ProjectGroup.objects.create(project=project, class_offering=project.class_offering)
    # Múltiplos grupos podem ser agendados na mesma sala e mesmo horário
    assert secretary.post(BASE + "showcase-planning/", payload, format="json").status_code == 200
    assert (
        secretary.post(
            BASE + "showcase-planning/",
            {
                **payload,
                "group": str(group2.pk),
            },
            format="json",
        ).status_code
        == 200
    )


@pytest.mark.django_db
def test_search_number_member_and_room_occupancy_not_filtered(planning):
    _, _, secretary, _, project, _, payload = planning
    secretary.post(BASE + "showcase-planning/", payload, format="json")
    data = secretary.get(BASE + "showcase-planning/", {"q": f"#{project.number}"}).json()
    assert data["groups"][0]["project"] == str(project.pk)
    assert data["groups"][0]["entry"]["room"] == payload["room"]
    member = project.groups.first().members.first().student.user
    data = secretary.get(BASE + "showcase-planning/", {"q": member.username}).json()
    assert len(data["groups"]) == 1
    data = secretary.get(BASE + "showcase-planning/", {"q": "__no_match__"}).json()
    assert data["groups"] == []
    assert len(data["entries"]) == 1


@pytest.mark.django_db
def test_forwarding_required_and_dates_validated(planning):
    student, _, secretary, _, project, _, payload = planning
    project.forwarding.delete()
    assert secretary.post(BASE + "showcase-planning/", payload, format="json").status_code == 400
    assert student.get(BASE + "showcase-planning/").status_code == 403
    for start, end in [("09:15", "10:00"), ("10:00", "09:00")]:
        assert (
            secretary.post(
                BASE + "showcase-days/",
                {
                    "date": "2026-12-11",
                    "start_time": start,
                    "end_time": end,
                },
                format="json",
            ).status_code
            == 400
        )
    assert (
        secretary.post(
            BASE + "showcase-days/",
            {
                "date": "2026-12-10",
                "start_time": "08:00",
                "end_time": "18:00",
            },
            format="json",
        ).status_code
        == 400
    )


@pytest.mark.django_db
def test_project_number_persisted_readonly_and_not_reused(planning):
    _, _, _, _, project, _, _ = planning
    number, identity = project.number, project.pk
    project.name = "Renomeado"
    project.save()
    project.refresh_from_db()
    assert (project.pk, project.number) == (identity, number)
    second = Project.objects.create(
        name="Segundo",
        about="Teste",
        created_by=project.created_by,
        class_offering=project.class_offering,
    )
    assert second.number > number


@pytest.mark.django_db
def test_cancel_then_reschedule_preserves_entry(planning):
    _, _, secretary, _, _, _, payload = planning
    response = secretary.post(BASE + "showcase-planning/", payload, format="json").json()
    cancelled = secretary.delete(BASE + f"showcase/{response['id']}/", {}, format="json").json()
    response2 = secretary.post(
        BASE + "showcase-planning/",
        {
            **payload,
            "expected_updated_at": cancelled["updated_at"],
        },
        format="json",
    )
    assert response2.status_code == 200
    assert response2.json()["id"] == response["id"]


@pytest.mark.django_db
def test_retired_prototype_cannot_be_written(planning):
    student, _, secretary, _, _, _, _ = planning
    assert secretary.post(BASE + "showcase-sessions/", {}, format="json").status_code == 410
    assert student.post(BASE + "showcase-sessions/", {}, format="json").status_code == 403
    assert APIClient().get(BASE + "showcase-planning/").status_code == 403


@pytest.mark.django_db
def test_legacy_entry_preserved_and_can_be_placed(planning):
    _, _, secretary, _, _, _, payload = planning
    entry = ShowcaseEntry.objects.create(
        group_id=payload["group"],
        date=timezone.make_aware(datetime(2026, 12, 10, 9)),
        location="Local antigo",
        status="SCHEDULED",
    )
    response = secretary.post(
        BASE + "showcase-planning/",
        {
            **payload,
            "expected_updated_at": entry.updated_at.isoformat(),
        },
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(entry.pk)


@pytest.mark.django_db
def test_legacy_notification_repair_only_unambiguous_titles(planning):
    _, _, secretary, _, project, _, _ = planning
    note = Notification.objects.create(
        user=secretary.handler._force_user,
        kind="PROJECT_FORWARDED",
        title=f"Encaminhamento recebido de {project.name}",
    )
    repair = import_module("projects.migrations.0023_repair_forwarding_notification_links")
    repair.repair_links(apps, SimpleNamespace(connection=connection))
    note.refresh_from_db()
    assert note.project_id == project.pk
    Project.objects.create(
        name=project.name,
        about="Homônimo",
        class_offering=project.class_offering,
        created_by=project.created_by,
    )
    ambiguous = Notification.objects.create(
        user=secretary.handler._force_user,
        kind="PROJECT_FORWARDED",
        title=f"Encaminhamento recebido de {project.name}",
    )
    repair.repair_links(apps, SimpleNamespace(connection=connection))
    ambiguous.refresh_from_db()
    assert ambiguous.project_id is None
