"""API views para a Sprint 7 — Mostra, publicação e acervo."""

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Project,
    Publication,
    PublicationDocument,
    ShowcaseEntry,
)
from .serializers import (
    PublicationCreateSerializer,
    PublicationDocumentCreateSerializer,
    PublicationDocumentReviewSerializer,
    PublicationDocumentSerializer,
    PublicationDocumentUpdateSerializer,
    PublicationSerializer,
    PublicationWithdrawSerializer,
    ShowcaseDirectGradeSerializer,
    ShowcaseEntryCreateSerializer,
    ShowcaseEntryPresenceSerializer,
    ShowcaseEntrySerializer,
    ShowcaseMemberAttendanceCreateSerializer,
)
from .showcase import (
    cancel_showcase_entry,
    create_showcase_entry,
    generate_publication_document,
    publish_project,
    record_member_attendance,
    record_presence,
    review_publication_document,
    withdraw_publication,
)


class _RequireShowcaseStaff(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and bool(
            request.user
            and request.user.is_active
            and request.user.role == "ADMIN"
        )


class _RequireEvaluator(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and bool(
            request.user
            and request.user.is_active
            and request.user.role == "PROFESSOR"
            and hasattr(request.user, "professor_profile")
        )


class ShowcaseEntryListCreateView(generics.ListCreateAPIView):
    """UC-018: Lista e agenda entradas na Mostra (administrador)."""

    pagination_class = None

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "GET" else [_RequireShowcaseStaff()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ShowcaseEntryCreateSerializer
        return ShowcaseEntrySerializer

    def get_queryset(self):
        queryset = (
            ShowcaseEntry.objects.select_related("group__project", "decided_by")
            .order_by("-date", "id")
            .all()
        )
        user = self.request.user
        if user.role == "ADMIN":
            return queryset
        return queryset.filter(group__evaluator__user=user)

    def perform_create(self, serializer):
        group = serializer.validated_data["group"]
        self._created_entry = create_showcase_entry(
            actor=self.request.user,
            group=group,
            date=serializer.validated_data["date"],
            location=serializer.validated_data["location"],
            notes=serializer.validated_data.get("notes", ""),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(
            ShowcaseEntrySerializer(self._created_entry, context={"request": request}).data
        )
        return Response(
            ShowcaseEntrySerializer(self._created_entry, context={"request": request}).data,
            status=201,
            headers=headers,
        )


class ShowcaseEntryDetailView(APIView):
    """Detalhe, cancelamento e registro de presença."""

    permission_classes = [IsAuthenticated]

    def get(self, request, entry_id):
        entry = get_object_or_404(
            ShowcaseEntry.objects.select_related("group__project", "decided_by"),
            pk=entry_id,
        )
        if request.user.role != "ADMIN":
            from .showcase import require_evaluator

            require_evaluator(request.user, entry.group)
        return Response(ShowcaseEntrySerializer(entry, context={"request": request}).data)

    def post(self, request, entry_id):
        """Avaliador registra presença (PRESENTED/ABSENT)."""
        entry = get_object_or_404(ShowcaseEntry.objects.select_related("group"), pk=entry_id)
        profile = getattr(request.user, "professor_profile", None)
        if not profile or entry.group.evaluator_id != profile.pk:
            raise PermissionDenied("Somente o avaliador designado pode registrar presença.")
        serializer = ShowcaseEntryPresenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = record_presence(
            actor=request.user,
            entry=entry,
            status=serializer.validated_data["status"],
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response(ShowcaseEntrySerializer(entry, context={"request": request}).data)

    def delete(self, request, entry_id):
        """Administrador cancela a entrada na Mostra."""
        if request.user.role != "ADMIN" or not request.user.is_active:
            raise PermissionDenied("Somente o Administrador pode cancelar.")
        entry = get_object_or_404(ShowcaseEntry.objects.select_related("group"), pk=entry_id)
        reason = request.data.get("reason", "") if request.data else ""
        entry = cancel_showcase_entry(actor=request.user, entry=entry, reason=reason)
        return Response(ShowcaseEntrySerializer(entry, context={"request": request}).data)


class ShowcaseEntryMemberAttendanceView(APIView):
    """Confirma a presença individual dos integrantes ativos."""

    permission_classes = [IsAuthenticated]

    def post(self, request, entry_id):
        entry = get_object_or_404(
            ShowcaseEntry.objects.select_related("group"), pk=entry_id
        )
        profile = getattr(request.user, "professor_profile", None)
        if not profile or entry.group.evaluator_id != profile.pk:
            raise PermissionDenied("Somente o avaliador designado pode registrar presença.")
        serializer = ShowcaseMemberAttendanceCreateSerializer(
            data=request.data, many=True
        )
        serializer.is_valid(raise_exception=True)
        entry = record_member_attendance(
            actor=request.user,
            entry=entry,
            member_attendances=serializer.validated_data,
        )
        return Response(
            ShowcaseEntrySerializer(
                entry, context={"request": request}
            ).data
        )


class ShowcaseEntryEvaluationView(APIView):
    permission_classes = [_RequireEvaluator]

    def post(self, request, entry_id):
        from .grading import submit_direct_grade

        entry = get_object_or_404(ShowcaseEntry.objects.select_related("group"), pk=entry_id)
        serializer = ShowcaseDirectGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submit_direct_grade(
            actor=request.user, entry=entry, value=serializer.validated_data["value"],
            comment=serializer.validated_data["observations"],
        )
        return Response(ShowcaseEntrySerializer(entry, context={"request": request}).data)


class PublicationDocumentListCreateView(generics.ListCreateAPIView):
    """Aluno lista e gera documentos publicáveis."""

    permission_classes = [IsAuthenticated]
    pagination_class = None
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PublicationDocumentCreateSerializer
        return PublicationDocumentSerializer

    def get_queryset(self):
        project_id = self.kwargs.get("project_id")
        from .services import accessible_project

        accessible_project(self.request.user, project_id)
        return (
            PublicationDocument.objects.filter(project_id=project_id)
            .select_related("reviewed_by", "generated_by", "consent_by")
            .order_by("-version")
        )

    def perform_create(self, serializer):
        project = get_object_or_404(Project, pk=self.kwargs.get("project_id"))
        document = generate_publication_document(
            actor=self.request.user,
            project=project,
            pdf_file=serializer.validated_data["pdf"],
            consent_given=serializer.validated_data.get("consent_given", False),
        )
        self._created_document = document

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(
            PublicationDocumentSerializer(
                self._created_document, context={"request": request}
            ).data
        )
        return Response(
            PublicationDocumentSerializer(
                self._created_document, context={"request": request}
            ).data,
            status=201,
            headers=headers,
        )


class PublicationDocumentReviewView(APIView):
    """Orientador aprova/reprova o documento."""

    permission_classes = [IsAuthenticated]

    def post(self, request, document_id):
        document = get_object_or_404(
            PublicationDocument.objects.select_related("project"), pk=document_id
        )
        profile = getattr(request.user, "professor_profile", None)
        if not profile or not document.project.groups.filter(
            responsible_professor=profile, is_active=True
        ).exists():
            raise PermissionDenied("Somente o orientador pode revisar o documento.")
        serializer = PublicationDocumentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if document.workflow != PublicationDocument.Workflow.LEGACY:
            from .publication_workflow import decide_document

            if serializer.validated_data["status"] != "APPROVED":
                raise ValidationError("Use o fluxo do acervo para enviar uma versão corrigida.")
            document = decide_document(actor=request.user, project_id=document.project_id,
                                       expected_document=document.pk, action="approve")
            return Response(PublicationDocumentSerializer(document).data)
        document = review_publication_document(
            actor=request.user,
            document=document,
            status=serializer.validated_data["status"],
            review=serializer.validated_data.get("review", ""),
        )
        return Response(PublicationDocumentSerializer(document, context={"request": request}).data)


class PublicationDocumentUpdateView(APIView):
    """Aluno edita o conteúdo do documento enquanto estiver pendente."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, document_id):
        document = get_object_or_404(
            PublicationDocument.objects.select_related("project"), pk=document_id
        )
        if document.generated_by_id != request.user.pk:
            raise PermissionDenied("Somente quem gerou o documento pode editá-lo.")
        if document.workflow != PublicationDocument.Workflow.LEGACY:
            raise ValidationError(
                "Versões enviadas são imutáveis. Envie uma nova versão pelo fluxo do acervo."
            )
        if document.status != PublicationDocument.Status.PENDING:
            raise ValidationError("Somente documentos pendentes podem ser editados.")
        serializer = PublicationDocumentUpdateSerializer(
            document, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            PublicationDocumentSerializer(document, context={"request": request}).data
        )


class PublicationDocumentDownloadView(APIView):
    """Download do PDF do documento (autorizado por objeto)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        document = get_object_or_404(
            PublicationDocument.objects.select_related("project"), pk=document_id
        )
        from .services import accessible_project
        accessible_project(request.user, document.project_id)
        response = FileResponse(document.pdf.open("rb"), content_type=document.content_type)
        response["Content-Disposition"] = f'attachment; filename="{document.original_name}"'
        return response


class PublicationListCreateView(generics.ListCreateAPIView):
    """Lista publicações e permite publicar (aluno + orientador)."""

    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PublicationCreateSerializer
        return PublicationSerializer

    def get_queryset(self):
        return (
            Publication.objects.select_related(
                "project", "document", "published_by_student", "withdrawn_by"
            )
            .filter(published_at__isnull=False, withdrawn_at__isnull=True)
            .order_by("-published_at")
        )

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        document = serializer.validated_data["document"]
        self._created_publication = publish_project(
            actor=self.request.user,
            project=project,
            document=document,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(
            PublicationSerializer(self._created_publication, context={"request": request}).data
        )
        return Response(
            PublicationSerializer(self._created_publication, context={"request": request}).data,
            status=201,
            headers=headers,
        )


class PublicationWithdrawView(APIView):
    """Administrador retira a publicação do acervo."""

    permission_classes = [_RequireShowcaseStaff]

    def post(self, request, publication_id):
        publication = get_object_or_404(
            Publication.objects.select_related("project"), pk=publication_id
        )
        serializer = PublicationWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        publication = withdraw_publication(
            actor=request.user,
            publication=publication,
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response(PublicationSerializer(publication, context={"request": request}).data)


class AcervoListView(generics.ListAPIView):
    """Página do acervo com pesquisa (usuários autenticados, minimização LGPD)."""

    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return (
            Publication.objects.select_related("project", "document")
            .filter(published_at__isnull=False, withdrawn_at__isnull=True)
            .order_by("-published_at")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        query = self.request.query_params.get("q", "").strip()[:100]
        for word in query.split():
            queryset = queryset.filter(
                project__name__icontains=word
            )
        # Nomes e resumo somente da versão publicada, sem RA/IDs/dados acadêmicos.
        data = [
            {
                "id": str(item.pk),
                "project_name": item.project.name,
                "document_version": item.document.version,
                "published_at": item.published_at,
                "created_at": item.created_at,
                "members": [
                    member["name"]
                    for member in item.document.snapshot.get("members", [])
                    if member.get("name")
                ],
                "abstract": item.document.abstract,
            }
            for item in queryset
        ]
        return Response(data)


class AcervoPDFView(APIView):
    """Leitura autenticada somente do documento vinculado à publicação vigente."""

    permission_classes = [IsAuthenticated]

    def get(self, request, publication_id):
        publication = get_object_or_404(
            Publication.objects.select_related("document"),
            pk=publication_id,
            published_at__isnull=False,
            withdrawn_at__isnull=True,
            document__status="APPROVED",
        )
        document = publication.document
        try:
            response = FileResponse(
                document.pdf.open("rb"),
                as_attachment=False,
                filename=document.original_name,
                content_type="application/pdf",
            )
        except FileNotFoundError as error:
            raise Http404("PDF indisponível.") from error
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class AcervoPublicListView(AcervoListView):
    """Consulta pública do acervo — mesmo conteúdo LGPD, sem exigir sessão."""

    permission_classes = [IsAuthenticatedOrReadOnly]


class ShowcaseSessionListCreateView(APIView):
    """Retired prototype: the supported workflow uses ShowcaseEntry and planning."""

    permission_classes = [_RequireShowcaseStaff]

    def get(self, request, **kwargs):
        return Response({"detail": "Use a agenda unificada em showcase-planning/."}, status=410)

    def post(self, request):
        return self.get(request)


class ShowcaseSessionDetailView(ShowcaseSessionListCreateView):

    def patch(self, request, session_id):
        return self.get(request)

    def delete(self, request, session_id):
        return self.get(request)
