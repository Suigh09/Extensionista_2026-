"""Formal delivery and forwarding endpoints (Sprint 5)."""

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .deliveries import forward_project, is_admin, review_delivery, submit_delivery
from .models import FormalDelivery, ProjectForwarding
from .permissions import IsProfessor
from .serializers import FormalDeliverySerializer, ProjectForwardingSerializer
from .services import accessible_project, can_access_project


def delivery_project(request, project_id):
    return accessible_project(request.user, project_id)


class DeliveryListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FormalDeliverySerializer
    pagination_class = None
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        project = delivery_project(self.request, self.kwargs["project_id"])
        return (
            FormalDelivery.objects.filter(project=project)
            .select_related("group", "submitted_by", "reviewed_by__user")
            .order_by("group_id", "version")
        )

    def post(self, request, project_id):
        project = delivery_project(request, project_id)
        uploaded = request.FILES.get("document")
        if uploaded is None:
            raise ValidationError({"document": "Anexe o documento da entrega."})
        notes = str(request.data.get("notes", ""))
        delivery = submit_delivery(
            actor=request.user, project=project, uploaded=uploaded, notes=notes
        )
        return Response(
            FormalDeliverySerializer(delivery).data, status=status.HTTP_201_CREATED
        )


class DeliveryReviewView(APIView):
    permission_classes = [IsAuthenticated, IsProfessor]

    def post(self, request, delivery_id):
        delivery = get_object_or_404(
            FormalDelivery.objects.select_related("project", "group"), pk=delivery_id
        )
        if not can_access_project(request.user, delivery.project):
            raise PermissionDenied("Você não tem acesso a este projeto.")
        decision = str(request.data.get("decision", "")).strip().upper()
        feedback = str(request.data.get("feedback", ""))
        reviewed = review_delivery(
            actor=request.user, delivery=delivery, decision=decision, feedback=feedback
        )
        return Response(FormalDeliverySerializer(reviewed).data)


class DeliveryDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, delivery_id):
        delivery = get_object_or_404(
            FormalDelivery.objects.select_related("project"), pk=delivery_id
        )
        forwarded = ProjectForwarding.objects.filter(
            project_id=delivery.project_id
        ).exists()
        if not (
            can_access_project(request.user, delivery.project)
            or (forwarded and is_admin(request.user))
        ):
            raise PermissionDenied("Você não tem acesso a este documento.")
        response = FileResponse(
            delivery.document.open("rb"),
            content_type=delivery.content_type,
            filename=delivery.original_name,
        )
        return response


class ForwardingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = delivery_project(request, project_id)
        forwarding = get_object_or_404(ProjectForwarding, project=project)
        return Response(ProjectForwardingSerializer(forwarding).data)

    def post(self, request, project_id):
        project = delivery_project(request, project_id)
        observations = str(request.data.get("observations", ""))
        required = str(request.data.get("required_competencies", ""))
        forwarding = forward_project(
            actor=request.user,
            project=project,
            observations=observations,
            required_competencies=required,
        )
        return Response(
            ProjectForwardingSerializer(forwarding).data,
            status=status.HTTP_201_CREATED,
        )


class ForwardedQueueView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectForwardingSerializer
    pagination_class = None

    def get_queryset(self):
        if not is_admin(self.request.user):
            raise PermissionDenied("Área disponível à Secretaria/Admin.")
        return ProjectForwarding.objects.select_related(
            "project", "forwarded_by"
        ).order_by("-forwarded_at", "project_id")
