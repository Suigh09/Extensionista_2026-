"""API autenticada do formulário, revisão, histórico e confirmação do acervo."""

from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Project, Publication
from .publication_workflow import (
    confirm_publication,
    decide_document,
    is_advisor,
    is_leader,
    latest_document,
    project_snapshot,
    publication_blockers,
    result_rows,
    submit_document,
)
from .serializers import PublicationDocumentSerializer
from .services import accessible_project, can_access_project


class WorkflowActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["submit", "approve", "correct", "accept", "publish"])
    expected_document = serializers.UUIDField(allow_null=True)
    title = serializers.CharField(max_length=180, required=False)
    abstract = serializers.CharField(max_length=4000, required=False)
    content = serializers.CharField(max_length=40000, required=False)
    consent = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if attrs["action"] in {"submit", "correct"}:
            for field in ("title", "abstract", "content"):
                if not attrs.get(field):
                    raise serializers.ValidationError({field: "Este campo é obrigatório."})
        return attrs


def workflow_data(actor, project):
    versions = project.publication_documents.select_related(
        "generated_by", "reviewed_by__user", "consent_by", "accepted_by"
    ).order_by("-version")
    latest = latest_document(project)
    blockers = publication_blockers(project)
    publication = Publication.objects.filter(project=project).first()
    return {
        "project": str(project.pk),
        "project_name": project.name,
        "number": project.number,
        "snapshot": project_snapshot(project),
        "blockers": blockers,
        "results": result_rows(project),
        "permissions": {
            "leader": is_leader(actor, project),
            "advisor": is_advisor(actor, project),
            "secretariat": actor.role == "ADMIN",
        },
        "versions": PublicationDocumentSerializer(versions, many=True).data,
        "state": "WITHDRAWN"
        if publication and publication.withdrawn_at
        else ("PUBLISHED" if publication else latest.workflow if latest else "NOT_STARTED"),
        "publication": str(publication.pk) if publication else None,
        "publication_detail": {
            "confirmed_by": publication.confirmed_by.get_full_name()
            if publication.confirmed_by
            else None,
            "published_at": publication.published_at,
            "withdrawn_at": publication.withdrawn_at,
        }
        if publication
        else None,
    }


class PublicationWorkflowView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        return Response(workflow_data(request.user, accessible_project(request.user, project_id)))

    def post(self, request, project_id):
        serializer = WorkflowActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        action = data.pop("action")
        if action == "submit":
            submit_document(actor=request.user, project_id=project_id, **data)
        elif action == "publish":
            confirm_publication(
                actor=request.user,
                project_id=project_id,
                expected_document=data["expected_document"],
            )
        else:
            decide_document(
                actor=request.user,
                project_id=project_id,
                action=action,
                expected_document=data["expected_document"],
                **{key: data[key] for key in ("title", "abstract", "content") if key in data},
            )
        return Response(workflow_data(request.user, get_object_or_404(Project, pk=project_id)))


class PublicationWorkflowQueueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = []
        for project in Project.objects.filter(is_active=True).order_by("number"):
            if not can_access_project(request.user, project):
                continue
            latest = latest_document(project)
            publication = Publication.objects.filter(project=project).first()
            rows.append(
                {
                    "id": str(project.pk),
                    "name": project.name,
                    "number": project.number,
                    "state": "WITHDRAWN"
                    if publication and publication.withdrawn_at
                    else (
                        "PUBLISHED" if publication else latest.workflow if latest else "NOT_STARTED"
                    ),
                }
            )
        return Response(rows)
