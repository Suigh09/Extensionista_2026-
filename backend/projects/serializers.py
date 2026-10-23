from html import escape
from html.parser import HTMLParser

from academic.models import ClassOffering, StudentProfile
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from .models import (
    CollaborationApplication,
    CollaborationOpportunity,
    Criterion,
    EvaluatorAssignment,
    FollowUp,
    FollowUpAttachment,
    FormalDelivery,
    GradeItem,
    GradeSubmission,
    GroupInvitation,
    GroupMember,
    IndividualGrade,
    Milestone,
    Project,
    ProjectForwarding,
    ProjectGroup,
    ProjectMilestone,
    ProjectTheme,
    Publication,
    PublicationDocument,
    Rubric,
    ShowcaseEntry,
)


class MemberSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="student.user_id", read_only=True)
    student_id = serializers.IntegerField(source="student.pk", read_only=True)
    name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    ra = serializers.CharField(source="student.ra", read_only=True)

    class Meta:
        model = GroupMember
        fields = ["user_id", "student_id", "name", "ra", "joined_at"]


class GroupSerializer(serializers.ModelSerializer):
    members = MemberSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    formation_status = serializers.SerializerMethodField()
    responsible_professor_name = serializers.CharField(
        source="responsible_professor.user.get_full_name",
        read_only=True,
        default=None,
    )
    evaluator_name = serializers.CharField(
        source="evaluator.user.get_full_name", read_only=True, default=None
    )
    leader_user_id = serializers.UUIDField(source="leader.user_id", read_only=True, default=None)

    class Meta:
        model = ProjectGroup
        fields = [
            "id",
            "name",
            "class_offering",
            "member_count",
            "formation_status",
            "members",
            "responsible_professor_name",
            "evaluator_name",
            "leader",
            "leader_user_id",
        ]

    def get_member_count(self, group):
        return sum(1 for member in group.members.all() if member.is_active)

    def get_formation_status(self, group):
        count = self.get_member_count(group)
        return "COMPLETE" if count == 4 else "FORMED" if count >= 2 else "FORMING"


class ProjectSerializer(serializers.ModelSerializer):
    group = serializers.SerializerMethodField()
    groups = GroupSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)
    lifecycle = serializers.SerializerMethodField()
    cancellation_requests = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    def get_can_manage(self, project):
        from rest_framework.exceptions import PermissionDenied

        from .lifecycle import require_project_manager
        request = self.context.get("request")
        if not request:
            return False
        try:
            require_project_manager(request.user, project)
            return True
        except PermissionDenied:
            return False

    def get_lifecycle(self, project):
        return [{"id": event.pk, "action": event.action, "previous_status": event.previous_status,
                 "new_status": event.new_status, "reason": event.reason,
                 "actor_name": event.actor.get_full_name(), "created_at": event.created_at}
                for event in project.state_events.select_related("actor").all()]

    def get_cancellation_requests(self, project):
        return [{"id": str(item.pk), "reason": item.reason, "status": item.status,
                  "requested_by_name": item.requested_by.get_full_name(),
                  "decision_note": item.decision_note,
                  "created_at": item.created_at, "decided_at": item.decided_at}
                for item in project.cancellation_requests.select_related("requested_by").all()]

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "about",
            "class_offering",
            "origin_room",
            "status",
            "is_active",
            "created_at",
            "updated_at",
            "group",
            "groups",
            "created_by_name",
            "submitted_at",
            "reviewed_at",
            "review_feedback",
            "reviewed_by",
            "theme",
            "theme_snapshot",
            "previous_status",
            "lifecycle",
            "cancellation_requests",
            "can_manage",
        ]
        read_only_fields = [
            "id",
            "class_offering",
            "origin_room",
            "status",
            "is_active",
            "created_at",
            "updated_at",
            "group",
            "groups",
            "created_by_name",
            "submitted_at",
            "reviewed_at",
            "review_feedback",
            "reviewed_by",
            "theme",
            "theme_snapshot",
            "previous_status",
            "lifecycle",
            "cancellation_requests",
            "can_manage",
        ]

    def validate_about(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Informe sobre o projeto.")
        return value

    def get_group(self, project):
        groups = list(project.groups.all())
        request = self.context.get("request")
        student_id = getattr(getattr(request, "user", None), "student_profile", None)
        student_id = getattr(student_id, "pk", None)
        group = next(
            (
                item
                for item in groups
                if any(
                    member.is_active and member.student_id == student_id
                    for member in item.members.all()
                )
            ),
            groups[0] if groups else None,
        )
        return GroupSerializer(group).data if group else None


class ProjectCreateSerializer(ProjectSerializer):
    class_offering = serializers.PrimaryKeyRelatedField(
        queryset=ClassOffering.objects.all(), required=False
    )
    theme = serializers.PrimaryKeyRelatedField(queryset=ProjectTheme.objects.all())
    leader = serializers.IntegerField(write_only=True, required=False, min_value=1)
    replace_active = serializers.BooleanField(write_only=True, required=False, default=False)
    student_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + ["replace_active", "leader", "student_ids"]

    def create(self, validated_data):
        validated_data.pop("replace_active", None)
        from .lifecycle import create_from_theme
        return create_from_theme(actor=self.context["request"].user,
            theme_id=validated_data.pop("theme").pk, leader_id=validated_data.pop("leader", None),
            student_ids=validated_data.pop("student_ids", None),
            name=validated_data["name"], about=validated_data["about"])

    def validate_class_offering(self, offering):
        student = getattr(self.context["request"].user, "student_profile", None)
        if not student:
            raise serializers.ValidationError("A turma é definida pelo aluno líder.")
        if not offering.is_active or student.class_offering_id != offering.pk:
            raise serializers.ValidationError("Turma inválida para o aluno.")
        return offering


class InvitationSerializer(serializers.ModelSerializer):
    invitee_user_id = serializers.UUIDField(source="invitee.user_id", read_only=True)
    invitee_name = serializers.CharField(source="invitee.user.get_full_name", read_only=True)
    invitee_ra = serializers.CharField(source="invitee.ra", read_only=True)
    project_name = serializers.CharField(source="group.project.name", read_only=True)

    class Meta:
        model = GroupInvitation
        fields = [
            "id",
            "group",
            "project_name",
            "invitee_user_id",
            "invitee_name",
            "invitee_ra",
            "status",
            "created_at",
            "decided_at",
        ]


class InvitationCreateSerializer(serializers.Serializer):
    invitee = serializers.PrimaryKeyRelatedField(
        queryset=StudentProfile.objects.select_related("user")
    )


class EligibleStudentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.get_full_name", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)
    class_code = serializers.CharField(source="class_offering.code", read_only=True, default="")
    term = serializers.CharField(source="class_offering.term", read_only=True, default="")

    class Meta:
        model = StudentProfile
        fields = ["id", "user", "name", "ra", "course_name", "class_code", "term"]


class SafeRichTextParser(HTMLParser):
    allowed_tags = {
        "p",
        "br",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "ul",
        "ol",
        "li",
        "h2",
        "h3",
        "blockquote",
        "a",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.allowed_tags:
            return
        safe_attrs = []
        if tag == "a":
            href = dict(attrs).get("href", "").strip()
            if href.startswith(("https://", "http://", "mailto:")):
                safe_attrs = [("href", href), ("rel", "noopener noreferrer"), ("target", "_blank")]
        rendered = "".join(f' {name}="{escape(value, quote=True)}"' for name, value in safe_attrs)
        self.output.append(f"<{tag}{rendered}>")

    def handle_endtag(self, tag):
        if tag in self.allowed_tags and tag != "br":
            self.output.append(f"</{tag}>")

    def handle_data(self, data):
        self.output.append(escape(data))


class FollowUpAttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = FollowUpAttachment
        fields = ["id", "original_name", "content_type", "size", "download_url"]

    def get_download_url(self, attachment):
        return f"/projects/attachments/{attachment.id}/download/"


class FollowUpSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True)
    author_role = serializers.CharField(source="author.role", read_only=True)
    attachments = FollowUpAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = FollowUp
        fields = [
            "id",
            "project",
            "author_name",
            "author_role",
            "text",
            "kind",
            "attachments",
            "created_at",
        ]
        read_only_fields = ["id", "project", "author_name", "author_role", "created_at"]

    def validate_text(self, value):
        parser = SafeRichTextParser()
        parser.feed(value.strip())
        value = "".join(parser.output).strip()
        plain = value.replace("<br>", "").replace("<p>", "").replace("</p>", "").strip()
        if not plain:
            raise serializers.ValidationError("Escreva uma atualização.")
        return value


class MilestoneSerializer(serializers.ModelSerializer):
    project_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False, max_length=100
    )
    class_offering = serializers.PrimaryKeyRelatedField(
        queryset=ClassOffering.objects.filter(is_active=True), write_only=True, required=False
    )
    project_count = serializers.SerializerMethodField(read_only=True)
    created_by_name = serializers.CharField(source="created_by.user.get_full_name", read_only=True)

    class Meta:
        model = Milestone
        fields = [
            "id",
            "title",
            "description",
            "due_at",
            "scope",
            "requires_delivery",
            "requires_approval",
            "created_by_name",
            "created_at",
            "project_count",
            "project_ids",
            "class_offering",
        ]
        read_only_fields = ["id", "created_by_name", "created_at", "project_count"]

    def validate(self, attrs):
        scope = attrs.get("scope")
        if scope == Milestone.Scope.CLASS and not attrs.get("class_offering"):
            raise serializers.ValidationError({"class_offering": "Informe a turma."})
        if scope == Milestone.Scope.PROJECTS and not attrs.get("project_ids"):
            raise serializers.ValidationError({"project_ids": "Selecione ao menos um projeto."})
        return attrs

    def get_project_count(self, milestone):
        return milestone.assignments.count()


class ProjectMilestoneSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="milestone.id", read_only=True)
    title = serializers.CharField(source="milestone.title", read_only=True)
    description = serializers.CharField(source="milestone.description", read_only=True)
    due_at = serializers.DateTimeField(source="milestone.due_at", read_only=True)
    requires_delivery = serializers.BooleanField(
        source="milestone.requires_delivery", read_only=True
    )
    requires_approval = serializers.BooleanField(
        source="milestone.requires_approval", read_only=True
    )
    created_by_name = serializers.CharField(
        source="milestone.created_by.user.get_full_name", read_only=True
    )

    class Meta:
        model = ProjectMilestone
        fields = [
            "id",
            "title",
            "description",
            "due_at",
            "requires_delivery",
            "requires_approval",
            "created_by_name",
            "assigned_at",
        ]


class CollaborationApplicationSerializer(serializers.ModelSerializer):
    candidate_group_name = serializers.CharField(source="candidate_group.name", read_only=True)
    candidate_project_name = serializers.CharField(
        source="candidate_group.project.name", read_only=True
    )
    candidate_class_label = serializers.CharField(
        source="candidate_group.class_offering.__str__", read_only=True
    )
    candidate_member_count = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = CollaborationApplication
        fields = [
            "id",
            "opportunity",
            "candidate_group",
            "candidate_group_name",
            "candidate_project_name",
            "candidate_class_label",
            "candidate_member_count",
            "message",
            "status",
            "created_at",
            "decided_at",
            "is_mine",
        ]
        read_only_fields = fields

    def get_candidate_member_count(self, application):
        return application.candidate_group.members.filter(is_active=True).count()

    def get_is_mine(self, application):
        user = getattr(self.context.get("request"), "user", None)
        return bool(user and application.created_by.user_id == user.pk)


class CollaborationOpportunitySerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(source="group.project_id", read_only=True)
    project_name = serializers.CharField(source="group.project.name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True)
    class_label = serializers.CharField(source="group.class_offering.__str__", read_only=True)
    member_count = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    applications = serializers.SerializerMethodField()

    class Meta:
        model = CollaborationOpportunity
        fields = [
            "id",
            "group",
            "project_id",
            "project_name",
            "group_name",
            "class_label",
            "member_count",
            "title",
            "description",
            "desired_skills",
            "status",
            "created_at",
            "updated_at",
            "is_owner",
            "applications",
        ]
        read_only_fields = [
            "id",
            "group",
            "project_id",
            "project_name",
            "group_name",
            "class_label",
            "member_count",
            "status",
            "created_at",
            "updated_at",
            "is_owner",
            "applications",
        ]

    def get_member_count(self, opportunity):
        return opportunity.group.members.filter(is_active=True).count()

    def get_is_owner(self, opportunity):
        user = getattr(self.context.get("request"), "user", None)
        return bool(
            user and opportunity.group.members.filter(student__user=user, is_active=True).exists()
        )

    def get_applications(self, opportunity):
        user = getattr(self.context.get("request"), "user", None)
        queryset = opportunity.applications.select_related(
            "candidate_group__project", "candidate_group__class_offering", "created_by__user"
        )
        if not user:
            return []
        if not opportunity.group.members.filter(student__user=user, is_active=True).exists():
            queryset = queryset.filter(created_by__user=user)
        return CollaborationApplicationSerializer(queryset, many=True, context=self.context).data

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Informe um título.")
        return value

    def validate_description(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Descreva a colaboração procurada.")
        return value

    def validate_desired_skills(self, value):
        if not isinstance(value, list) or len(value) > 10:
            raise serializers.ValidationError("Informe até dez competências.")
        return list(dict.fromkeys(str(item).strip()[:50] for item in value if str(item).strip()))


class CollaborationOpportunityCreateSerializer(CollaborationOpportunitySerializer):
    group = serializers.PrimaryKeyRelatedField(queryset=ProjectGroup.objects.filter(is_active=True))


class CollaborationApplicationCreateSerializer(serializers.Serializer):
    candidate_group = serializers.PrimaryKeyRelatedField(
        queryset=ProjectGroup.objects.filter(is_active=True)
    )
    message = serializers.CharField(
        max_length=1000, allow_blank=True, default="", trim_whitespace=True
    )


class FormalDeliverySerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True, default="")
    submitted_by_name = serializers.CharField(
        source="submitted_by.get_full_name", read_only=True
    )
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.user.get_full_name", read_only=True, default=None
    )
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = FormalDelivery
        fields = [
            "id",
            "project",
            "group",
            "group_name",
            "version",
            "title_snapshot",
            "about_snapshot",
            "notes",
            "original_name",
            "content_type",
            "size",
            "status",
            "submitted_by_name",
            "submitted_at",
            "review_feedback",
            "reviewed_by_name",
            "reviewed_at",
            "download_url",
        ]
        read_only_fields = fields

    def get_download_url(self, delivery):
        return f"/projects/deliveries/{delivery.pk}/download/"


class ProjectForwardingSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    forwarded_by_name = serializers.CharField(
        source="forwarded_by.get_full_name", read_only=True
    )

    class Meta:
        model = ProjectForwarding
        fields = [
            "project",
            "project_name",
            "snapshot",
            "observations",
            "required_competencies",
            "forwarded_by_name",
            "forwarded_at",
        ]
        read_only_fields = fields


class EvaluatorAssignmentSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True, default="")
    evaluator_name = serializers.CharField(
        source="evaluator.user.get_full_name", read_only=True
    )
    decided_by_name = serializers.CharField(
        source="decided_by.get_full_name", read_only=True
    )

    class Meta:
        model = EvaluatorAssignment
        fields = [
            "id",
            "group",
            "group_name",
            "evaluator",
            "evaluator_name",
            "recommended",
            "justification",
            "decided_by_name",
            "decided_at",
        ]
        read_only_fields = fields


class CriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Criterion
        fields = ["id", "name", "description", "position"]
        read_only_fields = ["id"]


class RubricSerializer(serializers.ModelSerializer):
    criteria = CriterionSerializer(many=True, read_only=True)

    class Meta:
        model = Rubric
        fields = ["id", "title", "criteria", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GradeItemSerializer(serializers.ModelSerializer):
    criterion_name = serializers.CharField(source="criterion.name", read_only=True)

    class Meta:
        model = GradeItem
        fields = ["criterion", "criterion_name", "value"]
        read_only_fields = fields


class GradeSubmissionSerializer(serializers.ModelSerializer):
    items = GradeItemSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source="author.get_full_name", read_only=True)
    rubric_title = serializers.CharField(source="rubric.title", read_only=True)

    class Meta:
        model = GradeSubmission
        fields = [
            "id",
            "group",
            "rubric",
            "rubric_title",
            "author_name",
            "comment",
            "concluded",
            "created_at",
            "items",
        ]
        read_only_fields = fields


class IndividualGradeSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True)
    student_name = serializers.CharField(
        source="student.user.get_full_name", read_only=True
    )

    class Meta:
        model = IndividualGrade
        fields = [
            "id",
            "student",
            "student_name",
            "group",
            "value",
            "comment",
            "author_name",
            "created_at",
        ]
        read_only_fields = fields


class ShowcaseEntrySerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True, default="")
    project_id = serializers.UUIDField(source="group.project_id", read_only=True)
    project_name = serializers.CharField(source="group.project.name", read_only=True, default="")
    decided_by_name = serializers.CharField(
        source="decided_by.get_full_name", read_only=True, default=None
    )
    is_evaluator = serializers.SerializerMethodField()

    class Meta:
        model = ShowcaseEntry
        fields = [
            "id",
            "group",
            "group_name",
            "project_id",
            "project_name",
            "date",
            "location",
            "status",
            "decided_by",
            "decided_by_name",
            "notes",
            "is_evaluator",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "group",
            "decided_by",
            "decided_by_name",
            "is_evaluator",
            "created_at",
            "updated_at",
        ]

    def get_is_evaluator(self, entry):
        user = getattr(self.context.get("request"), "user", None)
        if not user or user.role != "PROFESSOR":
            return False
        profile = getattr(user, "professor_profile", None)
        return bool(profile and entry.group.evaluator_id == profile.pk)

    def validate_date(self, value):
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("A data da Mostra deve ser futura.")
        return value

    def validate_location(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Informe o local da apresentação.")
        return value


class ShowcaseEntryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShowcaseEntry
        fields = ["group", "date", "location"]


class ShowcaseEntryPresenceSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[("PRESENTED", "Apresentado"), ("ABSENT", "Ausente")])
    notes = serializers.CharField(
        max_length=2000, allow_blank=True, default="", trim_whitespace=True
    )


class PublicationDocumentSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default="")
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.user.get_full_name", read_only=True, default=None
    )
    generated_by_name = serializers.CharField(
        source="generated_by.get_full_name", read_only=True
    )
    consent_by_name = serializers.CharField(
        source="consent_by.get_full_name", read_only=True, default=None
    )
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = PublicationDocument
        fields = [
            "id",
            "project",
            "project_name",
            "version",
            "original_name",
            "content_type",
            "size",
            "status",
            "review",
            "reviewed_by_name",
            "reviewed_at",
            "consent_given",
            "consent_at",
            "consent_by_name",
            "generated_by_name",
            "download_url",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "version",
            "original_name",
            "content_type",
            "size",
            "status",
            "review",
            "reviewed_by_name",
            "reviewed_at",
            "consent_given",
            "consent_at",
            "consent_by_name",
            "generated_by_name",
            "download_url",
            "created_at",
        ]

    def get_download_url(self, document):
        return f"/projects/publications/documents/{document.pk}/download/"


class PublicationDocumentCreateSerializer(serializers.ModelSerializer):
    pdf = serializers.FileField(required=True)

    class Meta:
        model = PublicationDocument
        fields = ["project", "pdf", "consent_given"]
        read_only_fields = ["project"]

    def validate_pdf(self, file):
        from pathlib import Path
        extension = Path(file.name).suffix.lower()
        if extension != ".pdf":
            raise serializers.ValidationError("O arquivo deve ser um PDF.")
        if file.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("O PDF deve ter no máximo 10 MB.")
        return file

    def validate(self, attrs):
        view = self.context.get("view")
        project_id = view.kwargs.get("project_id") if view else None
        if not project_id:
            raise serializers.ValidationError({"project": "Este campo é obrigatório."})
        from .models import Project
        project = get_object_or_404(Project, pk=project_id)
        attrs["project"] = project
        from .services import accessible_project
        request = self.context.get("request")
        if request:
            accessible_project(request.user, project.pk)
        if PublicationDocument.objects.filter(project=project).exists():
            last = PublicationDocument.objects.filter(project=project).order_by("-version").first()
            attrs["version"] = (last.version or 0) + 1
        else:
            attrs["version"] = 1
        return attrs


class PublicationDocumentReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[("APPROVED", "Aprovado"), ("REJECTED", "Reprovado")])
    review = serializers.CharField(
        max_length=2000, allow_blank=True, default="", trim_whitespace=True
    )


class PublicationSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default="")
    document_version = serializers.IntegerField(source="document.version", read_only=True)
    document_status = serializers.CharField(source="document.status", read_only=True)
    withdrawn_by_name = serializers.CharField(
        source="withdrawn_by.get_full_name", read_only=True, default=None
    )
    is_published = serializers.SerializerMethodField()

    class Meta:
        model = Publication
        fields = [
            "id",
            "project",
            "project_name",
            "document",
            "document_version",
            "document_status",
            "published_at",
            "withdrawn_at",
            "withdrawal_reason",
            "withdrawn_by_name",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_is_published(self, obj):
        return bool(obj.published_at and not obj.withdrawn_at)


class PublicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = ["project", "document"]

    def validate(self, attrs):
        project = attrs["project"]
        document = attrs["document"]
        if document.project_id != project.pk:
            raise serializers.ValidationError("O documento não pertence a este projeto.")
        if document.status != PublicationDocument.Status.APPROVED:
            raise serializers.ValidationError("O documento precisa estar aprovado para publicar.")
        if not document.consent_given:
            raise serializers.ValidationError(
                "O consentimento explícito é obrigatório para publicar."
            )
        from .services import accessible_project, require_approved_project
        request = self.context.get("request")
        if request:
            accessible_project(request.user, project.pk)
        require_approved_project(project)
        return attrs


class PublicationWithdrawSerializer(serializers.Serializer):
    reason = serializers.CharField(
        max_length=2000, allow_blank=True, default="", trim_whitespace=True
    )

