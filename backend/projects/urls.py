from django.urls import path

from .delivery_views import (
    DeliveryDownloadView,
    DeliveryListCreateView,
    DeliveryReviewView,
    ForwardedQueueView,
    ForwardingView,
)
from .evaluation_views import DesignateView, RecommendationView
from .grading_views import (
    ConcludeView,
    CriterionDetailView,
    CriterionListCreateView,
    GroupGradesView,
    RubricDetailView,
    RubricListCreateView,
    UsableRubricsView,
)
from .lifecycle_views import (
    InstitutionalProjectsView,
    ProjectAssignView,
    ProjectLifecycleView,
    ThemeDetailView,
    ThemeListView,
    ThemeStudentsView,
)
from .showcase_views import (
    AcervoListView,
    AcervoPublicListView,
    PublicationDocumentDownloadView,
    PublicationDocumentListCreateView,
    PublicationDocumentReviewView,
    PublicationListCreateView,
    PublicationWithdrawView,
    ShowcaseEntryDetailView,
    ShowcaseEntryListCreateView,
)
from .views import (
    AcceptCollaborationApplicationView,
    AcceptInvitationView,
    ApproveProjectView,
    CancelCollaborationApplicationView,
    CancelInvitationView,
    CollaborationApplicationCreateView,
    CollaborationOpportunityListCreateView,
    DeclineCollaborationApplicationView,
    DeclineInvitationView,
    EligibleStudentListView,
    FollowUpAttachmentDownloadView,
    FollowUpListCreateView,
    MilestoneListCreateView,
    MyInvitationListView,
    ProfessorProjectListView,
    ProjectDetailView,
    ProjectInvitationListCreateView,
    ProjectListCreateView,
    ProjectMilestoneListView,
    RequestProjectChangesView,
    SubmitProjectView,
    TimelineView,
)

urlpatterns = [
    path("themes/", ThemeListView.as_view()),
    path("themes/<uuid:theme_id>/", ThemeDetailView.as_view()),
    path("themes/<uuid:theme_id>/students/", ThemeStudentsView.as_view()),
    path("institutional/", InstitutionalProjectsView.as_view()),
    path("<uuid:project_id>/lifecycle/", ProjectLifecycleView.as_view()),
    path("<uuid:project_id>/assign-student/", ProjectAssignView.as_view()),
    path("", ProjectListCreateView.as_view(), name="project-list"),
    path("eligible-students/", EligibleStudentListView.as_view(), name="eligible-students"),
    path("invitations/mine/", MyInvitationListView.as_view(), name="my-invitations"),
    path("invitations/<uuid:invitation_id>/accept/", AcceptInvitationView.as_view()),
    path("invitations/<uuid:invitation_id>/decline/", DeclineInvitationView.as_view()),
    path("invitations/<uuid:invitation_id>/cancel/", CancelInvitationView.as_view()),
    path("available-to-professor/", ProfessorProjectListView.as_view()),
    path("attachments/<uuid:attachment_id>/download/", FollowUpAttachmentDownloadView.as_view()),
    path("milestones/", MilestoneListCreateView.as_view()),
    path("collaborations/opportunities/", CollaborationOpportunityListCreateView.as_view()),
    path(
        "collaborations/opportunities/<uuid:opportunity_id>/applications/",
        CollaborationApplicationCreateView.as_view(),
    ),
    path(
        "collaborations/applications/<uuid:application_id>/accept/",
        AcceptCollaborationApplicationView.as_view(),
    ),
    path(
        "collaborations/applications/<uuid:application_id>/decline/",
        DeclineCollaborationApplicationView.as_view(),
    ),
    path(
        "collaborations/applications/<uuid:application_id>/cancel/",
        CancelCollaborationApplicationView.as_view(),
    ),
    path("<uuid:project_id>/submit/", SubmitProjectView.as_view()),
    path("<uuid:project_id>/approve/", ApproveProjectView.as_view()),
    path("<uuid:project_id>/request-changes/", RequestProjectChangesView.as_view()),
    path("<uuid:project_id>/invitations/", ProjectInvitationListCreateView.as_view()),
    path("<uuid:project_id>/follow-ups/", FollowUpListCreateView.as_view()),
    path("<uuid:project_id>/milestones/", ProjectMilestoneListView.as_view()),
    path("<uuid:project_id>/timeline/", TimelineView.as_view()),
    path("<uuid:project_id>/deliveries/", DeliveryListCreateView.as_view()),
    path("<uuid:project_id>/forward/", ForwardingView.as_view()),
    path("forwarded/", ForwardedQueueView.as_view()),
    path("deliveries/<uuid:delivery_id>/review/", DeliveryReviewView.as_view()),
    path("deliveries/<uuid:delivery_id>/download/", DeliveryDownloadView.as_view()),
    path("<uuid:project_id>/evaluator-recommendations/", RecommendationView.as_view()),
    path(
        "groups/<uuid:group_id>/designate-evaluator/",
        DesignateView.as_view(),
    ),
    path("rubrics/", RubricListCreateView.as_view()),
    path("rubrics/<uuid:rubric_id>/", RubricDetailView.as_view()),
    path("rubrics/<uuid:rubric_id>/criteria/", CriterionListCreateView.as_view()),
    path("criteria/<uuid:criterion_id>/", CriterionDetailView.as_view()),
    path(
        "groups/<uuid:group_id>/grades/",
        GroupGradesView.as_view(),
    ),
    path(
        "groups/<uuid:group_id>/conclude/",
        ConcludeView.as_view(),
    ),
    path(
        "<uuid:project_id>/usable-rubrics/",
        UsableRubricsView.as_view(),
    ),
    path("<uuid:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    # Sprint 7 — Mostra
    path("showcase/", ShowcaseEntryListCreateView.as_view(), name="showcase-list"),
    path(
        "showcase/<uuid:entry_id>/",
        ShowcaseEntryDetailView.as_view(),
        name="showcase-detail",
    ),
    # Sprint 7 — Documento publicável
    path(
        "<uuid:project_id>/publication-documents/",
        PublicationDocumentListCreateView.as_view(),
        name="publication-document-list",
    ),
    path(
        "publication-documents/<uuid:document_id>/review/",
        PublicationDocumentReviewView.as_view(),
        name="publication-document-review",
    ),
    path(
        "publication-documents/<uuid:document_id>/download/",
        PublicationDocumentDownloadView.as_view(),
        name="publication-document-download",
    ),
    # Sprint 7 — Publicação/acervo
    path("publications/", PublicationListCreateView.as_view(), name="publication-list"),
    path(
        "publications/<uuid:publication_id>/withdraw/",
        PublicationWithdrawView.as_view(),
        name="publication-withdraw",
    ),
    path("acervo/", AcervoListView.as_view(), name="acervo-list"),
    path("acervo-publico/", AcervoPublicListView.as_view(), name="acervo-publico"),
]
