from accounts.models import AuditEvent
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    CollaborationApplication,
    CollaborationOpportunity,
    FollowUpAttachment,
    GroupInvitation,
    GroupMember,
    Milestone,
    Project,
    ProjectMilestone,
)
from .permissions import IsProfessor, IsStudent
from .serializers import (
    CollaborationApplicationCreateSerializer,
    CollaborationApplicationSerializer,
    CollaborationOpportunityCreateSerializer,
    CollaborationOpportunitySerializer,
    EligibleStudentSerializer,
    FollowUpSerializer,
    InvitationCreateSerializer,
    InvitationSerializer,
    MilestoneSerializer,
    ProjectCreateSerializer,
    ProjectMilestoneSerializer,
    ProjectSerializer,
)
from .services import (
    accessible_project,
    audit,
    create_collaboration_application,
    create_collaboration_opportunity,
    create_invitation,
    decide_collaboration_application,
    decide_invitation,
    require_approved_project,
    require_member,
    require_student,
)
from .uploads import validate_upload


class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        student = require_student(self.request.user)
        queryset = (
            Project.objects.filter(
                groups__members__student=student, groups__members__is_active=True
            )
            .select_related("class_offering")
            .prefetch_related("groups__members__student__user")
            .distinct()
            .order_by("-created_at")
        )
        query = self.request.query_params.get("q", "").strip()[:100]
        for word in query.split():
            queryset = queryset.filter(Q(name__icontains=word) | Q(about__icontains=word))
        return queryset

    def get_serializer_class(self):
        return ProjectCreateSerializer if self.request.method == "POST" else ProjectSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save()


class ProjectDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return Project.objects.filter(is_active=True).select_related("created_by").prefetch_related(
            "groups__members__student__user",
            "groups__responsible_professor__user",
            "groups__evaluator__user",
        )

    def get_object(self):
        return accessible_project(self.request.user, self.kwargs["pk"])

    @transaction.atomic
    def perform_update(self, serializer):
        from .lifecycle import require_project_manager
        serializer.instance = Project.objects.select_for_update().get(pk=serializer.instance.pk)
        require_project_manager(self.request.user, serializer.instance)
        if serializer.instance.status not in {
            Project.Status.DRAFT,
            Project.Status.CHANGES_REQUESTED,
        }:
            raise ValidationError("O projeto não pode ser editado nesta situação.")
        project = serializer.save()
        AuditEvent.objects.create(
            actor=self.request.user,
            action="UPDATE",
            object_type="projects.Project",
            object_id=str(project.pk),
            changed_fields=sorted(serializer.validated_data.keys()),
        )


class SubmitProjectView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    @transaction.atomic
    def post(self, request, project_id):
        project = accessible_project(request.user, project_id)
        project = Project.objects.select_for_update().get(pk=project.pk)
        group = project.groups.filter(is_active=True).first()
        if not group:
            raise ValidationError("O projeto não possui grupo ativo.")
        require_member(request.user, group)
        if group.members.filter(is_active=True).count() < 2:
            raise ValidationError(
                "Forme um grupo com pelo menos dois alunos antes de enviar o projeto."
            )
        if project.status not in {Project.Status.DRAFT, Project.Status.CHANGES_REQUESTED}:
            raise ValidationError("O projeto não pode ser enviado nesta situação.")
        if not group.responsible_professor_id:
            raise ValidationError("A turma precisa ter um professor orientador definido.")
        project.status = Project.Status.PENDING_APPROVAL
        project.submitted_at = timezone.now()
        project.review_feedback = ""
        project.save(update_fields=["status", "submitted_at", "review_feedback", "updated_at"])
        audit(request.user, "SUBMIT_PROJECT", project, ["status", "submitted_at"])
        from .lifecycle import record_event
        record_event(
            request.user,
            project,
            "SUBMIT_PROJECT",
            "DRAFT_OR_CHANGES",
            project.status,
            "Proposta enviada ao orientador.",
        )
        return Response(ProjectSerializer(project, context={"request": request}).data)


class ProjectReviewView(APIView):
    permission_classes = [IsAuthenticated, IsProfessor]
    decision = None

    @transaction.atomic
    def post(self, request, project_id):
        project = accessible_project(request.user, project_id)
        project = Project.objects.select_for_update().get(pk=project.pk)
        profile = request.user.professor_profile
        if not project.groups.filter(is_active=True, responsible_professor__pk=profile.pk).exists():
            raise PermissionDenied("Somente o professor orientador pode avaliar este projeto.")
        if project.status != Project.Status.PENDING_APPROVAL:
            raise ValidationError("O projeto não está aguardando aprovação.")
        feedback = str(request.data.get("feedback", "")).strip()[:2000]
        if self.decision == Project.Status.CHANGES_REQUESTED and not feedback:
            raise ValidationError({"feedback": "Informe os ajustes necessários."})
        previous = project.status
        project.status = self.decision
        project.review_feedback = feedback
        project.reviewed_at = timezone.now()
        project.reviewed_by = profile
        project.save(
            update_fields=[
                "status",
                "review_feedback",
                "reviewed_at",
                "reviewed_by",
                "updated_at",
            ]
        )
        audit(
            request.user,
            "REVIEW_PROJECT",
            project,
            ["status", "review_feedback", "reviewed_at", "reviewed_by"],
        )
        from .lifecycle import record_event
        record_event(
            request.user,
            project,
            "REVIEW_PROJECT",
            previous,
            project.status,
            feedback or "Proposta aprovada pelo orientador.",
        )
        if self.decision == Project.Status.CHANGES_REQUESTED:
            from accounts.models import Notification
            from accounts.notifications import notify

            members = GroupMember.objects.filter(
                group__project=project, group__is_active=True, is_active=True
            ).select_related("student__user")
            notify(
                [member.student.user for member in members],
                Notification.Kind.PROJECT_ADJUSTMENT_REQUESTED,
                f"Ajustes em {project.name}",
                feedback,
                project=project,
            )
        return Response(ProjectSerializer(project, context={"request": request}).data)


class ApproveProjectView(ProjectReviewView):
    decision = Project.Status.APPROVED


class RequestProjectChangesView(ProjectReviewView):
    decision = Project.Status.CHANGES_REQUESTED


class ProjectInvitationListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsStudent]
    pagination_class = None

    def project(self):
        return get_object_or_404(
            Project.objects.prefetch_related("groups"), pk=self.kwargs["project_id"]
        )

    def group(self):
        group = self.project().groups.filter(is_active=True).first()
        if not group:
            raise PermissionDenied("Grupo indisponível.")
        require_member(self.request.user, group)
        return group

    def get_serializer_class(self):
        return InvitationCreateSerializer if self.request.method == "POST" else InvitationSerializer

    def get_queryset(self):
        return (
            self.group()
            .invitations.select_related("invitee__user", "group__project")
            .order_by("-created_at")
        )

    def create(self, request, *args, **kwargs):
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = create_invitation(
            actor=request.user, group=self.group(), invitee=serializer.validated_data["invitee"]
        )
        return Response(InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)


class MyInvitationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsStudent]
    serializer_class = InvitationSerializer
    pagination_class = None

    def get_queryset(self):
        student = require_student(self.request.user)
        return (
            GroupInvitation.objects.filter(invitee=student)
            .select_related("invitee__user", "group__project")
            .order_by("-created_at")
        )


class InvitationDecisionView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]
    decision = None

    def post(self, request, invitation_id):
        invitation = get_object_or_404(GroupInvitation, pk=invitation_id)
        decided = decide_invitation(
            actor=request.user,
            invitation=invitation,
            decision=self.decision,
            replace_active=str(request.data.get("replace_active", "")).lower() == "true",
        )
        return Response(InvitationSerializer(decided).data)


class AcceptInvitationView(InvitationDecisionView):
    decision = GroupInvitation.Status.ACCEPTED


class DeclineInvitationView(InvitationDecisionView):
    decision = GroupInvitation.Status.DECLINED


class CancelInvitationView(InvitationDecisionView):
    decision = GroupInvitation.Status.CANCELLED


class EligibleStudentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsStudent]
    serializer_class = EligibleStudentSerializer
    pagination_class = None

    def get_queryset(self):
        student = require_student(self.request.user)
        room_membership = student.room_memberships.filter(
            is_active=True, room__status="ACTIVE"
        ).first()
        query = self.request.query_params.get("q", "").strip()
        if len(query) < 2 or not room_membership:
            return student.__class__.objects.none()
        queryset = (
            student.__class__.objects.filter(
                room_memberships__room_id=room_membership.room_id,
                room_memberships__is_active=True,
                user__is_active=True,
            )
            .exclude(pk=student.pk)
            .select_related("user", "course", "class_offering")
        )
        queryset = queryset.filter(
            Q(ra__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
        )
        project_id = self.request.query_params.get("project", "").strip()
        if project_id:
            project = get_object_or_404(Project, pk=project_id, is_active=True)
            group = project.groups.filter(is_active=True).first()
            if not group:
                raise PermissionDenied("Grupo indisponível.")
            require_member(self.request.user, group)
            queryset = queryset.exclude(
                group_memberships__group=group, group_memberships__is_active=True
            ).exclude(
                group_invitations__group=group,
                group_invitations__status=GroupInvitation.Status.PENDING,
            )
        return queryset.order_by("user__first_name", "user__last_name")[:6]


class FollowUpListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FollowUpSerializer
    pagination_class = None
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def project(self):
        return accessible_project(self.request.user, self.kwargs["project_id"])

    def get_queryset(self):
        return self.project().follow_ups.select_related("author").prefetch_related("attachments")

    @transaction.atomic
    def perform_create(self, serializer):
        project = Project.objects.select_for_update().get(pk=self.project().pk)
        paused_approved = (
            project.status == Project.Status.PAUSED
            and project.previous_status == Project.Status.APPROVED
        )
        if not paused_approved:
            require_approved_project(project)
        files = self.request.FILES.getlist("attachments")
        if len(files) > 10:
            raise ValidationError("Envie no máximo 10 arquivos por publicação.")
        validated = [validate_upload(uploaded) for uploaded in files]
        follow_up = serializer.save(project=project, author=self.request.user)
        for uploaded, (original_name, content_type, size) in zip(
            files, validated, strict=False
        ):
            FollowUpAttachment.objects.create(
                follow_up=follow_up,
                file=uploaded,
                original_name=original_name,
                content_type=content_type[:120],
                size=size,
            )
        audit(self.request.user, "FOLLOW_UP", follow_up, ["text", "kind"])


class FollowUpAttachmentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, attachment_id):
        attachment = get_object_or_404(
            FollowUpAttachment.objects.select_related("follow_up__project"), pk=attachment_id
        )
        accessible_project(request.user, attachment.follow_up.project_id)
        response = FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=attachment.original_name,
            content_type=attachment.content_type,
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        audit(request.user, "DOWNLOAD", attachment, ["file"])
        return response


class ProjectMilestoneListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectMilestoneSerializer
    pagination_class = None

    def get_queryset(self):
        project = accessible_project(self.request.user, self.kwargs["project_id"])
        require_approved_project(project)
        return project.milestone_assignments.select_related("milestone__created_by__user")


class TimelineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = accessible_project(request.user, project_id)
        items = [
            {
                "id": str(item.pk),
                "event_type": "FOLLOW_UP",
                "occurred_at": item.created_at,
                "title": item.author.get_full_name() or item.author.username,
                "description": item.text,
                "author_role": item.author.role,
                "attachments": FollowUpSerializer(item).data["attachments"],
            }
            for item in project.follow_ups.select_related("author").prefetch_related("attachments")
        ]
        items.sort(key=lambda item: (item["occurred_at"], item["id"]))
        return Response(items)


class ProfessorProjectListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsProfessor]
    serializer_class = ProjectSerializer
    pagination_class = None

    def get_queryset(self):
        profile = self.request.user.professor_profile
        return (
            Project.objects.filter(
                is_active=True,
                groups__is_active=True,
            ).filter(
                Q(groups__responsible_professor=profile) | Q(groups__evaluator=profile)
            )
            .prefetch_related("groups__members__student__user")
            .distinct()
            .order_by("name")
        )


class MilestoneListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsProfessor]
    serializer_class = MilestoneSerializer
    pagination_class = None

    def get_queryset(self):
        return Milestone.objects.filter(
            created_by=self.request.user.professor_profile
        ).prefetch_related("assignments")

    @transaction.atomic
    def perform_create(self, serializer):
        profile = self.request.user.professor_profile
        project_ids = serializer.validated_data.pop("project_ids", [])
        offering = serializer.validated_data.pop("class_offering", None)
        if offering and not profile.class_offerings.filter(pk=offering.pk).exists():
            raise PermissionDenied("Turma não vinculada ao professor.")
        allowed = Project.objects.filter(
            is_active=True,
            status=Project.Status.APPROVED,
            groups__is_active=True,
            groups__class_offering__in=profile.class_offerings.all(),
        )
        projects = (
            allowed.filter(groups__class_offering=offering).distinct()
            if offering
            else allowed.filter(pk__in=project_ids).distinct()
        )
        if not projects.exists() or (project_ids and projects.count() != len(set(project_ids))):
            raise PermissionDenied("Um ou mais projetos não estão sob sua responsabilidade.")
        milestone = serializer.save(created_by=profile)
        ProjectMilestone.objects.bulk_create(
            [ProjectMilestone(milestone=milestone, project=project) for project in projects]
        )
        audit(
            self.request.user,
            "CREATE_MILESTONE",
            milestone,
            ["title", "description", "due_at", "scope", "requires_delivery", "requires_approval"],
        )


class CollaborationOpportunityListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsStudent]
    pagination_class = None

    def get_serializer_class(self):
        return (
            CollaborationOpportunityCreateSerializer
            if self.request.method == "POST"
            else CollaborationOpportunitySerializer
        )

    def get_queryset(self):
        student = require_student(self.request.user)
        queryset = (
            CollaborationOpportunity.objects.filter(
                Q(status=CollaborationOpportunity.Status.OPEN)
                | Q(group__members__student=student, group__members__is_active=True)
                | Q(applications__created_by=student)
            )
            .select_related("group__project", "group__class_offering")
            .prefetch_related("group__members", "applications__candidate_group__members")
            .distinct()
        )
        query = self.request.query_params.get("q", "").strip()[:100]
        for word in query.split():
            queryset = queryset.filter(
                Q(group__project__name__icontains=word) | Q(group__project__about__icontains=word)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = CollaborationOpportunityCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        opportunity = create_collaboration_opportunity(
            actor=request.user,
            group=serializer.validated_data["group"],
            title=serializer.validated_data["title"],
            description=serializer.validated_data["description"],
            desired_skills=serializer.validated_data.get("desired_skills", []),
        )
        return Response(
            CollaborationOpportunitySerializer(opportunity, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CollaborationApplicationCreateView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, opportunity_id):
        serializer = CollaborationApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opportunity = get_object_or_404(CollaborationOpportunity, pk=opportunity_id)
        application = create_collaboration_application(
            actor=request.user,
            opportunity=opportunity,
            candidate_group=serializer.validated_data["candidate_group"],
            message=serializer.validated_data["message"],
        )
        return Response(
            CollaborationApplicationSerializer(application, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CollaborationApplicationDecisionView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]
    decision = None

    def post(self, request, application_id):
        application = get_object_or_404(CollaborationApplication, pk=application_id)
        decided = decide_collaboration_application(
            actor=request.user, application=application, decision=self.decision
        )
        return Response(
            CollaborationApplicationSerializer(decided, context={"request": request}).data
        )


class AcceptCollaborationApplicationView(CollaborationApplicationDecisionView):
    decision = CollaborationApplication.Status.ACCEPTED


class DeclineCollaborationApplicationView(CollaborationApplicationDecisionView):
    decision = CollaborationApplication.Status.DECLINED


class CancelCollaborationApplicationView(CollaborationApplicationDecisionView):
    decision = CollaborationApplication.Status.CANCELLED
