# ruff: noqa: F811 - fixture compartilhada importada de test_projects.
import hashlib

import pytest
from academic.models import ProfessorProfile
from accounts.models import Notification, User
from projects.models import GroupMember, Publication, PublicationDocument
from rest_framework.test import APIClient

from .test_projects import academic_context  # noqa: F401
from .test_showcase import approved_project, pdf, setup

BASE = "/api/v1/projects/"
pytestmark = pytest.mark.django_db


@pytest.fixture
def workflow(academic_context, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    offering, _, leader, second, member, _, advisor, secretary, admin, stranger = setup(
        academic_context
    )
    project = approved_project(leader, offering)
    group_id = project["groups"][0]["id"]
    GroupMember.objects.create(group_id=group_id, student=second)
    delivery = leader.post(
        f"{BASE}{project['id']}/deliveries/", {"document": pdf()}, format="multipart"
    )
    assert delivery.status_code == 201, delivery.content
    reviewed = advisor.post(
        f"{BASE}deliveries/{delivery.json()['id']}/review/", {"decision": "APPROVED"}
    )
    assert reviewed.status_code == 200, reviewed.content
    forwarded = advisor.post(f"{BASE}{project['id']}/forward/", {}, format="json")
    assert forwarded.status_code == 201, forwarded.content
    user = User.objects.create_user(username="workflow-evaluator", role="PROFESSOR")
    professor = ProfessorProfile.objects.create(user=user, registration="WF-EVAL")
    from projects.models import ProjectGroup

    group = ProjectGroup.objects.get(pk=group_id)
    group.evaluator = professor
    group.save(update_fields=["evaluator"])
    evaluator = APIClient()
    evaluator.force_authenticate(user)
    entry = secretary.post(
        f"{BASE}showcase/",
        {"group": group_id, "date": "2026-12-10T14:00:00Z", "location": "Sala 1"},
        format="json",
    )
    assert entry.status_code == 201, entry.content
    entry_id = entry.json()["id"]
    attendance = evaluator.post(
        f"{BASE}showcase/{entry_id}/member-attendance/",
        [
            {"member_id": item.pk, "present": item.student_id != second.pk}
            for item in group.members.filter(is_active=True)
        ],
        format="json",
    )
    assert attendance.status_code == 200, attendance.content
    graded = evaluator.post(
        f"{BASE}showcase/{entry_id}/evaluation/",
        {"value": "8.75", "observations": "Grupo bem preparado."},
        format="json",
    )
    assert graded.status_code == 200, graded.content
    return {
        "project": project,
        "group": group,
        "leader": leader,
        "member": member,
        "advisor": advisor,
        "secretary": secretary,
        "admin": admin,
        "stranger": stranger,
        "evaluator": evaluator,
        "url": f"{BASE}{project['id']}/publication-workflow/",
    }


def submit_version(flow):
    response = flow["leader"].post(
        flow["url"],
        {
            "action": "submit",
            "expected_document": None,
            "title": "Educação e extensão",
            "abstract": "Resumo com ação e inclusão.",
            "content": "Texto original\n\nSegunda seção <texto> & conteúdo.",
            "consent": True,
        },
        format="json",
    )
    assert response.status_code == 200, response.content
    return response.json()["versions"][0]


def action(flow, actor, name, document, **extra):
    return flow[actor].post(
        flow["url"], {"action": name, "expected_document": document["id"], **extra}, format="json"
    )


def test_full_flow_approval_without_edits(workflow):
    flow = workflow
    note = Notification.objects.get(
        user=flow["advisor"].handler._force_user, kind="SHOWCASE_RESULTS"
    )
    assert note.project_id == flow["group"].project_id
    result = flow["advisor"].get(flow["url"]).json()
    assert result["blockers"] == []
    assert result["results"][0]["grade"] == "8.75"
    assert {item["present"] for item in result["results"][0]["members"]} == {True, False}
    assert not result["permissions"]["leader"]
    first = submit_version(flow)
    assert first["workflow"] == "ADVISOR"
    assert first["version"] == 1
    doc = PublicationDocument.objects.get(pk=first["id"])
    with doc.pdf.open("rb") as file:
        data = file.read()
    assert data.startswith(b"%PDF-") and len(data) > 1000
    assert hashlib.sha256(data).hexdigest() == first["pdf_sha256"]
    assert "ra" not in first["snapshot"]["members"][0]
    assert "grade" not in first["snapshot"]
    assert action(flow, "secretary", "publish", first).status_code == 400
    approved = action(flow, "advisor", "approve", first)
    assert approved.status_code == 200, approved.content
    assert approved.json()["state"] == "SECRETARIAT"
    assert not Publication.objects.exists()
    published = action(flow, "secretary", "publish", first)
    assert published.status_code == 200, published.content
    assert published.json()["state"] == "PUBLISHED"
    publication = Publication.objects.get()
    assert publication.confirmed_by_id == flow["secretary"].handler._force_user.pk
    assert publication.document_id == doc.pk
    assert action(flow, "admin", "publish", first).status_code == 400
    assert (
        action(flow, "advisor", "correct", first, title="x", abstract="y", content="z").status_code
        == 400
    )
    public = APIClient().get(f"{BASE}acervo-publico/")
    assert public.status_code == 200
    assert len(public.json()) == 1
    assert APIClient().get(f"{BASE}publication-documents/{doc.pk}/download/").status_code == 403


def test_correction_requires_leader_acceptance_preserves_versions(workflow):
    flow = workflow
    first = submit_version(flow)
    corrected = action(
        flow,
        "advisor",
        "correct",
        first,
        title=first["title"],
        abstract="Resumo corrigido.",
        content="Texto revisado pelo orientador.",
    )
    assert corrected.status_code == 200, corrected.content
    second = corrected.json()["versions"][0]
    assert second["workflow"] == "LEADER"
    assert second["parent"] == first["id"]
    assert second["version"] == 2
    assert second["pdf_sha256"] != first["pdf_sha256"]
    old = PublicationDocument.objects.get(pk=first["id"])
    assert old.content == first["content"]
    assert old.pdf_sha256 == first["pdf_sha256"]
    assert action(flow, "secretary", "publish", second).status_code == 400
    assert action(flow, "member", "accept", second).status_code == 403
    assert action(flow, "advisor", "accept", second).status_code == 403
    assert action(flow, "leader", "accept", first).status_code == 400
    assert action(flow, "leader", "accept", second).status_code == 200
    assert action(flow, "secretary", "publish", first).status_code == 400
    assert action(flow, "secretary", "publish", second).status_code == 200
    assert Publication.objects.get().document_id == old.revisions.get().pk
    assert flow["member"].get(flow["url"]).json()["versions"][0]["accepted_by_name"] is not None


@pytest.mark.parametrize("actor", ["member", "advisor", "secretary", "evaluator"])
def test_only_leader_submits(workflow, actor):
    response = workflow[actor].post(
        workflow["url"],
        {
            "action": "submit",
            "expected_document": None,
            "title": "Título",
            "abstract": "Resumo",
            "content": "Texto",
            "consent": True,
        },
        format="json",
    )
    assert response.status_code == 403
    assert not PublicationDocument.objects.exists()


def test_no_shortcuts_no_stale_approval_and_immutable_text(workflow):
    flow = workflow
    first = submit_version(flow)
    for actor in ("leader", "member", "evaluator", "secretary"):
        assert action(flow, actor, "approve", first).status_code == 403
    assert (
        flow["leader"]
        .patch(
            f"{BASE}publication-documents/{first['id']}/content/",
            {"content": "Sobrescrever"},
            format="json",
        )
        .status_code
        == 400
    )
    second = flow["leader"].post(
        flow["url"],
        {
            "action": "submit",
            "expected_document": first["id"],
            "title": "Novo",
            "abstract": "Resumo",
            "content": "Novo texto",
            "consent": True,
        },
        format="json",
    )
    assert second.status_code == 200
    assert action(flow, "advisor", "approve", first).status_code == 400
    doc = second.json()["versions"][0]
    assert action(flow, "advisor", "approve", doc).status_code == 200
    for actor in ("leader", "member", "advisor", "evaluator"):
        assert action(flow, actor, "publish", doc).status_code == 403
        response = flow[actor].post(
            f"{BASE}publications/",
            {"project": flow["project"]["id"], "document": doc["id"]},
            format="json",
        )
        assert response.status_code == 403
    assert not Publication.objects.exists()


def test_object_authorization_and_queue(workflow):
    flow = workflow
    first = submit_version(flow)
    stranger = flow["stranger"]
    assert stranger.get(flow["url"]).status_code == 404
    assert stranger.get(f"{BASE}{flow['project']['id']}/publication-documents/").status_code == 404
    assert stranger.get(f"{BASE}publication-documents/{first['id']}/download/").status_code in {
        403,
        404,
    }
    assert stranger.get(f"{BASE}publication-workflow/").json() == []
    assert flow["advisor"].get(f"{BASE}publication-workflow/").json()[0]["state"] == "ADVISOR"


@pytest.mark.parametrize("missing", ["delivery", "forwarding", "attendance", "grade", "presented"])
def test_prerequisites_cannot_be_skipped(workflow, missing):
    group = workflow["group"]
    if missing == "delivery":
        group.deliveries.update(status="CHANGES_REQUESTED")
    elif missing == "forwarding":
        group.project.forwarding.delete()
    elif missing == "attendance":
        group.showcase_entry.member_attendances.all().delete()
    elif missing == "grade":
        group.grade_submissions.update(concluded=False)
    else:
        group.showcase_entry.status = "ABSENT"
        group.showcase_entry.save()
    response = workflow["leader"].post(
        workflow["url"],
        {
            "action": "submit",
            "expected_document": None,
            "title": "Título",
            "abstract": "Resumo",
            "content": "Texto",
            "consent": True,
        },
        format="json",
    )
    assert response.status_code == 400
    assert not PublicationDocument.objects.exists()


def test_consent_and_pdf_render_failure_roll_back(workflow, monkeypatch):
    flow = workflow
    payload = {
        "action": "submit",
        "expected_document": None,
        "title": "Título",
        "abstract": "Resumo",
        "content": "Texto",
        "consent": False,
    }
    assert flow["leader"].post(flow["url"], payload, format="json").status_code == 400
    from projects import publication_pdf

    def fail(**kwargs):
        raise OSError("PDF indisponível")

    monkeypatch.setattr(publication_pdf, "render_publication_pdf", fail)
    with pytest.raises(OSError):
        flow["leader"].post(flow["url"], {**payload, "consent": True}, format="json")
    assert not PublicationDocument.objects.exists()
