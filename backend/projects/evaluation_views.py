"""Evaluator recommendation and designation endpoints (Sprint 5.1)."""

from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .evaluation import (
    auto_allocate_evaluators,
    designate_evaluator,
    evaluator_options,
    recommend_evaluators,
)
from .lifecycle import is_admin
from .models import EvaluatorAssignment, ProjectGroup, ShowcaseDay, ShowcaseRoom
from .serializers import EvaluatorAssignmentSerializer
from .services import accessible_project


class RecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = accessible_project(request.user, project_id)
        if not is_admin(request.user):
            raise PermissionDenied("Área disponível à Secretaria/Admin.")
        table = recommend_evaluators(project)
        groups = (
            project.groups.filter(is_active=True)
            .select_related("responsible_professor__user", "evaluator__user")
            .order_by("created_at", "id")
        )
        history = EvaluatorAssignment.objects.filter(group__project=project).select_related(
            "group", "evaluator__user", "decided_by"
        )
        return Response(
            {
                **table,
                "groups": [
                    {
                        "group_id": str(group.pk),
                        "group_name": group.name,
                        "responsible_professor_name": (
                            group.responsible_professor.user.get_full_name()
                            if group.responsible_professor
                            else None
                        ),
                        "evaluator_profile_id": str(group.evaluator_id)
                        if group.evaluator_id
                        else None,
                        "evaluator_name": (
                            group.evaluator.user.get_full_name() if group.evaluator else None
                        ),
                    }
                    for group in groups
                ],
                "history": EvaluatorAssignmentSerializer(history, many=True).data,
            }
        )


class DesignationInput(serializers.Serializer):
    professor = serializers.IntegerField(min_value=1, max_value=2**63 - 1)
    justification = serializers.CharField(max_length=2000, allow_blank=True, default="")


class DesignateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        try:
            group = ProjectGroup.objects.select_related("project").get(pk=group_id, is_active=True)
        except ProjectGroup.DoesNotExist as error:
            from rest_framework.exceptions import NotFound

            raise NotFound("Grupo não encontrado.") from error
        accessible_project(request.user, group.project_id)
        serializer = DesignationInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = designate_evaluator(
            actor=request.user,
            group=group,
            professor_profile_id=str(serializer.validated_data["professor"]),
            justification=serializer.validated_data["justification"],
        )
        return Response(
            EvaluatorAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


class GroupEvaluatorOptionsView(APIView):
    def get(self, request, group_id):
        if not is_admin(request.user):
            raise PermissionDenied("Área disponível à Secretaria/Admin.")
        group = get_object_or_404(
            ProjectGroup.objects.select_related("project", "evaluator__user", "showcase_entry"),
            pk=group_id,
            is_active=True,
            project__is_active=True,
        )
        return Response(
            {
                **evaluator_options(group),
                "group": str(group.pk),
                "current": str(group.evaluator_id) if group.evaluator_id else None,
                "current_name": (
                    group.evaluator.user.get_full_name() or group.evaluator.user.username
                    if group.evaluator_id
                    else None
                ),
            }
        )


class AutoAllocationInput(serializers.Serializer):
    day = serializers.UUIDField()
    room = serializers.UUIDField()


class AutoEvaluatorAllocationView(APIView):
    def post(self, request):
        if not is_admin(request.user):
            raise PermissionDenied("Somente a Secretaria/Admin aloca avaliadores.")
        serializer = AutoAllocationInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        day = get_object_or_404(ShowcaseDay, pk=serializer.validated_data["day"])
        room = get_object_or_404(ShowcaseRoom, pk=serializer.validated_data["room"])
        return Response(auto_allocate_evaluators(actor=request.user, day=day, room=room))
