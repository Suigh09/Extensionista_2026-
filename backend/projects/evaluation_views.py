"""Evaluator recommendation and designation endpoints (Sprint 5.1)."""

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .evaluation import designate_evaluator, recommend_evaluators
from .lifecycle import is_admin
from .models import EvaluatorAssignment, ProjectGroup
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
        history = EvaluatorAssignment.objects.filter(
            group__project=project
        ).select_related("group", "evaluator__user", "decided_by")
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
                            group.evaluator.user.get_full_name()
                            if group.evaluator
                            else None
                        ),
                    }
                    for group in groups
                ],
                "history": EvaluatorAssignmentSerializer(history, many=True).data,
            }
        )


class DesignateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        try:
            group = ProjectGroup.objects.select_related("project").get(
                pk=group_id, is_active=True
            )
        except ProjectGroup.DoesNotExist as error:
            from rest_framework.exceptions import NotFound

            raise NotFound("Grupo não encontrado.") from error
        accessible_project(request.user, group.project_id)
        assignment = designate_evaluator(
            actor=request.user,
            group=group,
            professor_profile_id=str(request.data.get("professor") or ""),
            justification=str(request.data.get("justification") or ""),
        )
        return Response(
            EvaluatorAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )
