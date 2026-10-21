"""Rubric and grading endpoints (Sprint 6)."""

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .grading import (
    add_criterion,
    conclude_evaluation,
    create_rubric,
    delete_criterion,
    grade_student,
    group_grade_value,
    submit_grades,
    update_rubric_title,
    usable_rubrics,
)
from .models import Criterion, GradeSubmission, IndividualGrade, ProjectGroup, Rubric
from .permissions import IsProfessor
from .serializers import (
    CriterionSerializer,
    GradeSubmissionSerializer,
    IndividualGradeSerializer,
    RubricSerializer,
)
from .services import accessible_project, can_access_project


class RubricListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsProfessor]
    serializer_class = RubricSerializer
    pagination_class = None

    def get_queryset(self):
        from academic.models import ProfessorProfile

        profile = ProfessorProfile.objects.filter(user=self.request.user).first()
        if profile is None:
            return Rubric.objects.none()
        return Rubric.objects.filter(owner=profile).prefetch_related("criteria")

    def post(self, request):
        rubric = create_rubric(
            actor=request.user,
            title=request.data.get("title", ""),
            criteria=request.data.get("criteria", []),
        )
        return Response(
            RubricSerializer(rubric).data, status=status.HTTP_201_CREATED
        )


class RubricDetailView(APIView):
    permission_classes = [IsAuthenticated, IsProfessor]

    def patch(self, request, rubric_id):
        rubric = get_object_or_404(Rubric, pk=rubric_id)
        updated = update_rubric_title(
            actor=request.user, rubric=rubric, title=request.data.get("title", "")
        )
        return Response(RubricSerializer(updated).data)

    def delete(self, request, rubric_id):
        from .grading import owner_profile

        rubric = get_object_or_404(Rubric, pk=rubric_id)
        profile = owner_profile(request.user)
        if profile is None or rubric.owner_id != profile.pk:
            raise PermissionDenied("Rubrica indisponível.")
        if GradeSubmission.objects.filter(rubric=rubric).exists():
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Rubrica já utilizada em avaliações.")
        rubric.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CriterionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsProfessor]
    serializer_class = CriterionSerializer
    pagination_class = None

    def get_queryset(self):
        rubric = get_object_or_404(Rubric, pk=self.kwargs["rubric_id"])
        from .grading import _owned_rubric

        _owned_rubric(self.request.user, rubric.pk)
        return rubric.criteria.all()

    def post(self, request, rubric_id):
        rubric = get_object_or_404(Rubric, pk=rubric_id)
        criterion = add_criterion(
            actor=request.user,
            rubric=rubric,
            name=request.data.get("name", ""),
            description=request.data.get("description", ""),
        )
        return Response(
            CriterionSerializer(criterion).data, status=status.HTTP_201_CREATED
        )


class CriterionDetailView(APIView):
    permission_classes = [IsAuthenticated, IsProfessor]

    def delete(self, request, criterion_id):
        criterion = get_object_or_404(
            Criterion.objects.select_related("rubric"), pk=criterion_id
        )
        delete_criterion(actor=request.user, criterion=criterion)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UsableRubricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = accessible_project(request.user, project_id)
        rubrics = usable_rubrics(request.user, project).prefetch_related("criteria")
        return Response(RubricSerializer(rubrics, many=True).data)


class GroupGradesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        group = get_object_or_404(
            ProjectGroup.objects.select_related("project"), pk=group_id
        )
        if not can_access_project(request.user, group.project):
            raise PermissionDenied("Você não tem acesso a este projeto.")
        submissions = (
            GradeSubmission.objects.filter(group=group)
            .select_related("rubric", "author")
            .prefetch_related("items__criterion")
            .order_by("-created_at", "-id")
        )
        average, _ = group_grade_value(group)
        return Response(
            {
                "average": str(average) if average is not None else None,
                "submissions": GradeSubmissionSerializer(submissions, many=True).data,
            }
        )

    def post(self, request, group_id):
        group = get_object_or_404(ProjectGroup.objects.select_related("project"), pk=group_id)
        if not can_access_project(request.user, group.project):
            raise PermissionDenied("Você não tem acesso a este projeto.")
        submission = submit_grades(
            actor=request.user,
            group=group,
            rubric_id=str(request.data.get("rubric", "")),
            items=request.data.get("items", []),
            comment=str(request.data.get("comment", "")),
        )
        average, _ = group_grade_value(group)
        return Response(
            {**GradeSubmissionSerializer(submission).data, "average": str(average)},
            status=status.HTTP_201_CREATED,
        )


class ConcludeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(ProjectGroup.objects.select_related("project"), pk=group_id)
        if not can_access_project(request.user, group.project):
            raise PermissionDenied("Você não tem acesso a este projeto.")
        latest = conclude_evaluation(actor=request.user, group=group)
        return Response(GradeSubmissionSerializer(latest).data)


class IndividualGradeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        from academic.models import StudentProfile

        try:
            student = StudentProfile.objects.select_related("user").get(pk=student_id)
        except (StudentProfile.DoesNotExist, ValueError, TypeError) as error:
            raise NotFound("Aluno não encontrado.") from error
        memberships = student.group_memberships.filter(
            group__is_active=True, is_active=True
        ).select_related("group__project")
        visible = any(
            can_access_project(request.user, membership.group.project)
            for membership in memberships
        )
        if not visible:
            raise PermissionDenied("Você não tem acesso a este aluno.")
        history = (
            IndividualGrade.objects.filter(student=student)
            .select_related("author")
            .order_by("-created_at", "-id")
        )
        current = history.first()
        return Response(
            {
                "current": IndividualGradeSerializer(current).data if current else None,
                "history": IndividualGradeSerializer(history, many=True).data,
            }
        )

    def post(self, request, student_id):
        grade = grade_student(
            actor=request.user,
            student_id=str(student_id),
            value=request.data.get("value"),
            comment=str(request.data.get("comment", "")),
        )
        return Response(
            IndividualGradeSerializer(grade).data, status=status.HTTP_201_CREATED
        )
