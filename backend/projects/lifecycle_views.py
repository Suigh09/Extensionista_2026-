from academic.models import AcademicRoom, RoomMembership, StudentProfile
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .lifecycle import assign_student, is_admin, require_room_manager, transition
from .models import Project, ProjectTheme
from .serializers import EligibleStudentSerializer, ProjectSerializer
from .services import accessible_project, audit


class ThemeSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source="room.name", read_only=True)
    project_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectTheme
        fields = [
            "id",
            "room",
            "room_name",
            "title",
            "description",
            "is_open",
            "max_projects",
            "is_template",
            "interdisciplinary",
            "project_count",
        ]
        read_only_fields = ["id", "room_name", "project_count"]

    def get_project_count(self, obj):
        return obj.projects.count()

    def validate_max_projects(self, value):
        if value is not None and value < 1:
            raise ValidationError("O limite deve ser positivo ou vazio para ilimitado.")
        if self.instance and value is not None and value < self.instance.projects.count():
            raise ValidationError(
                "O limite não pode ser menor que a quantidade de projetos existentes."
            )
        return value


class ThemeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        themes = ProjectTheme.objects.select_related("room")
        if request.user.role == "STUDENT":
            themes = themes.filter(
                room__memberships__student__user=request.user,
                room__memberships__is_active=True,
                room__status="ACTIVE",
                is_open=True,
            )
            is_template = request.query_params.get("is_template", "").strip().lower()
            if is_template == "true":
                themes = themes.filter(is_template=True)
            interdisciplinary = request.query_params.get("interdisciplinary", "").strip().lower()
            if interdisciplinary == "true":
                themes = themes.filter(interdisciplinary=True)
        elif not is_admin(request.user):
            themes = themes.filter(room__responsible_professor__user=request.user)
        for word in request.query_params.get("q", "")[:100].split():
            themes = themes.filter(Q(title__icontains=word) | Q(description__icontains=word))
        return Response(ThemeSerializer(themes, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = ThemeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = AcademicRoom.objects.select_for_update().get(pk=serializer.validated_data["room"].pk)
        require_room_manager(request.user, room)
        if room.status != "ACTIVE":
            raise ValidationError("Temas só podem ser publicados em salas ativas.")
        theme = serializer.save()
        audit(request.user, "CREATE_THEME", theme, ["title", "description", "room"])
        return Response(ThemeSerializer(theme).data, status=201)


class ThemeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, theme_id):
        theme = get_object_or_404(
            ProjectTheme.objects.select_for_update().select_related("room"),
            pk=theme_id,
        )
        require_room_manager(request.user, theme.room)
        if "room" in request.data:
            raise ValidationError("O tema não pode ser transferido entre salas.")
        if theme.room.status != "ACTIVE":
            raise ValidationError("A sala está encerrada.")
        serializer = ThemeSerializer(theme, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(request.user, "UPDATE_THEME", theme, list(serializer.validated_data))
        return Response(serializer.data)


class ThemeStudentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, theme_id):
        theme = get_object_or_404(ProjectTheme.objects.select_related("room"), pk=theme_id)
        if request.user.role == "STUDENT":
            student_profile = getattr(request.user, "student_profile", None)
            if not student_profile or not RoomMembership.objects.filter(
                room=theme.room, student=student_profile, is_active=True
            ).exists():
                raise PermissionDenied("Somente membros da sala podem consultar alunos elegíveis.")
        else:
            require_room_manager(request.user, theme.room)
        query = request.query_params.get("q", "").strip()[:100]
        students = StudentProfile.objects.none()
        if len(query) >= 2:
            students = StudentProfile.objects.filter(
                room_memberships__room=theme.room,
                room_memberships__is_active=True,
                user__is_active=True,
            ).select_related("user", "course", "class_offering")
            for word in query.split():
                students = students.filter(
                    Q(user__first_name__icontains=word)
                    | Q(user__last_name__icontains=word)
                    | Q(ra__icontains=word)
                )
        return Response(
            EligibleStudentSerializer(
                students.order_by("user__first_name", "user__last_name")[:8],
                many=True,
            ).data
        )


class ProjectLifecycleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        class Command(serializers.Serializer):
            action = serializers.ChoiceField(
                choices=[
                    "pause",
                    "resume",
                    "request-cancellation",
                    "cancel",
                    "approve-cancellation",
                    "decline-cancellation",
                ]
            )
            reason = serializers.CharField(max_length=2000, allow_blank=False)
        command = Command(data=request.data)
        command.is_valid(raise_exception=True)
        project = transition(
            actor=request.user,
            project=accessible_project(request.user, project_id),
            **command.validated_data,
        )
        return Response(ProjectSerializer(project, context={"request": request}).data)


class ProjectAssignView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        class Command(serializers.Serializer):
            student_id = serializers.IntegerField(min_value=1)
            make_leader = serializers.BooleanField(default=False)
        command = Command(data=request.data)
        command.is_valid(raise_exception=True)
        project = assign_student(
            actor=request.user,
            project=accessible_project(request.user, project_id),
            **command.validated_data,
        )
        return Response(ProjectSerializer(project, context={"request": request}).data)


class InstitutionalProjectsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework.exceptions import PermissionDenied
        if not is_admin(request.user):
            raise PermissionDenied("Área disponível à Secretaria/Admin.")
        return Response(
            ProjectSerializer(
                Project.objects.filter(is_active=True)
                .prefetch_related("groups__members__student__user")
                .order_by("-created_at"),
                many=True,
                context={"request": request},
            ).data
        )
