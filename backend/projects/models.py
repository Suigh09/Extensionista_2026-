import uuid
from pathlib import Path

from academic.models import AcademicRoom, ClassOffering, ProfessorProfile, StudentProfile
from django.conf import settings
from django.db import models
from django.db.models import Q


class Project(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Aguardando aprovação"
        CHANGES_REQUESTED = "CHANGES_REQUESTED", "Ajustes solicitados"
        APPROVED = "APPROVED", "Aprovado"
        COMPLETED = "COMPLETED", "Concluído"
        ARCHIVED = "ARCHIVED", "Arquivado"
        PAUSED = "PAUSED", "Pausado"
        CANCELLED = "CANCELLED", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=180)
    about = models.TextField()
    theme = models.ForeignKey(
        "ProjectTheme",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="projects",
    )
    theme_snapshot = models.JSONField(default=dict, blank=True)
    origin_template = models.ForeignKey(
        "ProjectTheme",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="projects_from_template",
    )
    previous_status = models.CharField(max_length=20, blank=True)
    class_offering = models.ForeignKey(
        ClassOffering, on_delete=models.PROTECT, related_name="projects"
    )
    origin_room = models.ForeignKey(
        AcademicRoom, null=True, blank=True, on_delete=models.PROTECT, related_name="projects"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_projects"
    )
    is_active = models.BooleanField(default=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_feedback = models.TextField(blank=True, max_length=2000)
    reviewed_by = models.ForeignKey(
        ProfessorProfile, null=True, blank=True, on_delete=models.PROTECT,
        related_name="reviewed_projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        super().save(*args, **kwargs)


class ProjectGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="groups")
    class_offering = models.ForeignKey(
        ClassOffering, on_delete=models.PROTECT, related_name="project_groups"
    )
    name = models.CharField(max_length=120, blank=True)
    leader = models.ForeignKey(
        StudentProfile,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="led_groups",
    )
    responsible_professor = models.ForeignKey(
        ProfessorProfile, null=True, blank=True, on_delete=models.PROTECT,
        related_name="responsible_project_groups",
    )
    evaluator = models.ForeignKey(
        ProfessorProfile, null=True, blank=True, on_delete=models.PROTECT,
        related_name="evaluated_project_groups",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class GroupMember(models.Model):
    group = models.ForeignKey(ProjectGroup, on_delete=models.PROTECT, related_name="members")
    student = models.ForeignKey(
        StudentProfile, on_delete=models.PROTECT, related_name="group_memberships"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["group", "student"], name="unique_group_member")
        ]
        indexes = [models.Index(fields=["student", "is_active"])]


class ProjectTheme(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(AcademicRoom, on_delete=models.PROTECT, related_name="themes")
    title = models.CharField(max_length=180)
    description = models.TextField(max_length=6000)
    is_open = models.BooleanField(default=True)
    max_projects = models.PositiveIntegerField(null=True, blank=True)
    is_template = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(max_projects__isnull=True) | Q(max_projects__gte=1),
                name="theme_positive_limit",
            )
        ]


class ActiveGroupSlot(models.Model):
    """Unique reservation; historical GroupMember rows are never removed."""
    student = models.OneToOneField(
        StudentProfile,
        primary_key=True,
        on_delete=models.PROTECT,
        related_name="active_group_slot",
    )
    group = models.ForeignKey(ProjectGroup, on_delete=models.PROTECT, related_name="active_slots")


class CancellationRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, related_name="cancellation_requests"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="project_cancellations",
    )
    reason = models.CharField(max_length=2000)
    status = models.CharField(
        max_length=10,
        choices=[
            ("PENDING", "Pendente"),
            ("APPROVED", "Aprovado"),
            ("DECLINED", "Recusado"),
        ],
        default="PENDING",
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.PROTECT,
        related_name="decided_cancellations",
    )
    decision_note = models.CharField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project"],
                condition=Q(status="PENDING"),
                name="one_pending_project_cancellation",
            )
        ]


class ProjectStateEvent(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="state_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=40)
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    reason = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class GroupInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        ACCEPTED = "ACCEPTED", "Aceito"
        DECLINED = "DECLINED", "Recusado"
        CANCELLED = "CANCELLED", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(ProjectGroup, on_delete=models.PROTECT, related_name="invitations")
    invitee = models.ForeignKey(
        StudentProfile, on_delete=models.PROTECT, related_name="group_invitations"
    )
    invited_by = models.ForeignKey(
        StudentProfile, on_delete=models.PROTECT, related_name="sent_group_invitations"
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "invitee"],
                condition=Q(status="PENDING"),
                name="unique_pending_group_invitation",
            )
        ]
        indexes = [models.Index(fields=["invitee", "status"])]


class CollaborationOpportunity(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Aberta"
        MATCHED = "MATCHED", "Parceria formada"
        CLOSED = "CLOSED", "Encerrada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        ProjectGroup, on_delete=models.PROTECT, related_name="collaboration_opportunities"
    )
    title = models.CharField(max_length=160)
    description = models.TextField(max_length=2000)
    desired_skills = models.JSONField(default=list)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(
        StudentProfile, on_delete=models.PROTECT, related_name="collaboration_opportunities"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["group"],
                condition=Q(status="OPEN"),
                name="unique_open_collaboration_opportunity",
            )
        ]
        indexes = [models.Index(fields=["status", "created_at"])]


class CollaborationApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        ACCEPTED = "ACCEPTED", "Aceita"
        DECLINED = "DECLINED", "Recusada"
        CANCELLED = "CANCELLED", "Cancelada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(
        CollaborationOpportunity, on_delete=models.PROTECT, related_name="applications"
    )
    candidate_group = models.ForeignKey(
        ProjectGroup, on_delete=models.PROTECT, related_name="collaboration_applications"
    )
    message = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_by = models.ForeignKey(
        StudentProfile, on_delete=models.PROTECT, related_name="collaboration_applications"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["opportunity", "candidate_group"],
                condition=Q(status="PENDING"),
                name="unique_pending_collaboration_application",
            )
        ]
        indexes = [models.Index(fields=["opportunity", "status"])]


class FollowUp(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="follow_ups")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="project_follow_ups"
    )
    text = models.TextField(max_length=5000)
    kind = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["project", "created_at"])]


def follow_up_attachment_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"project-publications/{instance.follow_up.project_id}/{uuid.uuid4().hex}{extension}"


class FollowUpAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    follow_up = models.ForeignKey(FollowUp, on_delete=models.PROTECT, related_name="attachments")
    file = models.FileField(upload_to=follow_up_attachment_path, max_length=300)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    size = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


def delivery_document_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"project-deliveries/{instance.project_id}/{uuid.uuid4().hex}{extension}"


class FormalDelivery(models.Model):
    """Immutable versioned formal delivery of a group; distinct from follow-ups."""

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Enviada"
        APPROVED = "APPROVED", "Aprovada"
        CHANGES_REQUESTED = "CHANGES_REQUESTED", "Ajustes solicitados"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="deliveries")
    group = models.ForeignKey(
        ProjectGroup, on_delete=models.PROTECT, related_name="deliveries"
    )
    version = models.PositiveIntegerField()
    title_snapshot = models.CharField(max_length=180)
    about_snapshot = models.TextField()
    notes = models.TextField(max_length=2000, blank=True)
    document = models.FileField(upload_to=delivery_document_path, max_length=300)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    size = models.PositiveBigIntegerField()
    status = models.CharField(max_length=17, choices=Status.choices, default=Status.SUBMITTED)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submitted_deliveries"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    review_feedback = models.TextField(max_length=2000, blank=True)
    reviewed_by = models.ForeignKey(
        ProfessorProfile,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reviewed_deliveries",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["project", "group", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "group", "version"], name="unique_delivery_version"
            ),
            models.UniqueConstraint(
                fields=["project", "group"],
                condition=Q(status="SUBMITTED"),
                name="one_pending_delivery_per_group",
            ),
        ]
        indexes = [models.Index(fields=["project", "group", "version"])]


class ProjectForwarding(models.Model):
    """Explicit forwarding of an approved project to the secretariat (one-way)."""

    project = models.OneToOneField(
        Project, on_delete=models.PROTECT, related_name="forwarding"
    )
    snapshot = models.JSONField(default=dict, blank=True)
    observations = models.TextField(max_length=2000, blank=True)
    required_competencies = models.TextField(max_length=2000, blank=True)
    forwarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="forwarded_projects"
    )
    forwarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-forwarded_at", "project_id"]


class Milestone(models.Model):
    class Scope(models.TextChoices):
        PROJECTS = "PROJECTS", "Projetos selecionados"
        CLASS = "CLASS", "Turma"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    due_at = models.DateTimeField()
    scope = models.CharField(max_length=16, choices=Scope.choices)
    requires_delivery = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "academic.ProfessorProfile", on_delete=models.PROTECT, related_name="milestones"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_at", "id"]


class ProjectMilestone(models.Model):
    milestone = models.ForeignKey(Milestone, on_delete=models.PROTECT, related_name="assignments")
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, related_name="milestone_assignments"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["milestone", "project"], name="unique_project_milestone"
            )
        ]
        indexes = [models.Index(fields=["project", "assigned_at"])]


class EvaluatorAssignment(models.Model):
    """Auditable history of evaluator designations; group.evaluator is the latest."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        ProjectGroup, on_delete=models.PROTECT, related_name="evaluator_assignments"
    )
    evaluator = models.ForeignKey(
        "academic.ProfessorProfile",
        on_delete=models.PROTECT,
        related_name="evaluator_assignments",
    )
    recommended = models.JSONField(default=list, blank=True)
    justification = models.CharField(max_length=2000, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="decided_evaluator_assignments",
    )
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["decided_at", "id"]
        indexes = [models.Index(fields=["group", "decided_at"])]


class Rubric(models.Model):
    """Reusable professor catalog for group evaluation (Sprint 6)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        "academic.ProfessorProfile", on_delete=models.PROTECT, related_name="rubrics"
    )
    title = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title", "id"]


class Criterion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rubric = models.ForeignKey(Rubric, on_delete=models.PROTECT, related_name="criteria")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["rubric", "name"], name="unique_rubric_criterion_name"
            )
        ]


class GradeSubmission(models.Model):
    """Immutable round of group grades; latest per group is vigente."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        ProjectGroup, on_delete=models.PROTECT, related_name="grade_submissions"
    )
    rubric = models.ForeignKey(Rubric, on_delete=models.PROTECT, related_name="submissions")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="grade_submissions"
    )
    comment = models.TextField(max_length=2000, blank=True)
    concluded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["group", "created_at"])]


class GradeItem(models.Model):
    submission = models.ForeignKey(
        GradeSubmission, on_delete=models.PROTECT, related_name="items"
    )
    criterion = models.ForeignKey(
        Criterion, on_delete=models.PROTECT, related_name="grade_items"
    )
    value = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "criterion"], name="unique_submission_criterion"
            ),
            models.CheckConstraint(
                condition=Q(value__gte=0) & Q(value__lte=10), name="grade_value_range"
            ),
        ]


class IndividualGrade(models.Model):
    """Immutable orientador grade per student; latest per student is vigente."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        "academic.StudentProfile",
        on_delete=models.PROTECT,
        related_name="individual_grades",
    )
    group = models.ForeignKey(
        ProjectGroup, on_delete=models.PROTECT, related_name="individual_grades"
    )
    value = models.DecimalField(max_digits=4, decimal_places=2)
    comment = models.TextField(max_length=2000, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="given_individual_grades",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(value__gte=0) & Q(value__lte=10),
                name="individual_grade_value_range",
            )
        ]
        indexes = [models.Index(fields=["student", "created_at"])]


class ShowcaseEntry(models.Model):
    """Agenda e presença da Mostra Extensionista por grupo encaminhado."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        SCHEDULED = "SCHEDULED", "Agendado"
        PRESENTED = "PRESENTED", "Apresentado"
        ABSENT = "ABSENT", "Ausente"
        CANCELLED = "CANCELLED", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.OneToOneField(
        ProjectGroup, on_delete=models.PROTECT, related_name="showcase_entry"
    )
    date = models.DateTimeField()
    location = models.CharField(max_length=200)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="showcase_decisions",
    )
    notes = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "id"]
        indexes = [
            models.Index(fields=["group", "status"]),
            models.Index(fields=["status", "date"]),
        ]


def publication_document_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"project-publications/{instance.project_id}/{uuid.uuid4().hex}{extension}"


class PublicationDocument(models.Model):
    """Versioned publicable document generated by the student."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        APPROVED = "APPROVED", "Aprovado"
        REJECTED = "REJECTED", "Reprovado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, related_name="publication_documents"
    )
    version = models.PositiveIntegerField()
    content = models.TextField(blank=True, default="")
    pdf = models.FileField(upload_to=publication_document_path, max_length=300)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    size = models.PositiveBigIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    review = models.TextField(max_length=2000, blank=True)
    reviewed_by = models.ForeignKey(
        "academic.ProfessorProfile", null=True, blank=True, on_delete=models.PROTECT,
        related_name="reviewed_publication_documents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    consent_given = models.BooleanField(default=False)
    consent_at = models.DateTimeField(null=True, blank=True)
    consent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="consented_publications",
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="generated_documents"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["project", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "version"], name="unique_publication_document_version"
            ),
        ]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]


class Publication(models.Model):
    """Publicação no acervo; retirada preserva o histórico."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        Project, on_delete=models.PROTECT, related_name="publication"
    )
    document = models.ForeignKey(
        PublicationDocument, on_delete=models.PROTECT, related_name="publications"
    )
    published_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawal_reason = models.TextField(max_length=2000, blank=True)
    withdrawn_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="withdrawn_publications",
    )
    published_by_student = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="published_projects_as_student",
    )
    published_by_professor = models.ForeignKey(
        "academic.ProfessorProfile", null=True, blank=True, on_delete=models.PROTECT,
        related_name="published_projects_as_professor",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project"]),
            models.Index(fields=["published_at", "withdrawn_at"]),
        ]
