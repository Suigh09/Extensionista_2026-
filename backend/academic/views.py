from accounts.models import AuditEvent
from accounts.permissions import IsAcademicStaff
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AcademicRoom,
    ClassOffering,
    Course,
    ProfessorExpertise,
    ProfessorProfile,
    RoomTransferRequest,
    StudentProfile,
    Subject,
)
from .serializers import (
    AcademicRoomSerializer,
    ClassOfferingSerializer,
    CourseSerializer,
    EligibleRoomStudentSerializer,
    ProfessorExpertiseSerializer,
    ProfessorProfileSerializer,
    RoomMembershipSerializer,
    RoomTransferRequestSerializer,
    StudentProfileSerializer,
    SubjectSerializer,
)
from .services import (
    audit,
    close_room,
    decide_transfer,
    pull_student,
    require_owned_room,
    require_professor,
)


class AuditedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAcademicStaff]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def audit(self, instance, action, fields):
        AuditEvent.objects.create(
            actor=self.request.user,
            action=action,
            object_type=instance._meta.label,
            object_id=str(instance.pk),
            changed_fields=sorted(fields),
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        self.audit(instance, "CREATE", serializer.validated_data.keys())

    def perform_update(self, serializer):
        instance = serializer.save()
        self.audit(instance, "UPDATE", serializer.validated_data.keys())


class CourseViewSet(AuditedViewSet):
    queryset = Course.objects.order_by("name")
    serializer_class = CourseSerializer
    search_fields = ["code", "name"]
    ordering_fields = ["code", "name", "created_at"]


class SubjectViewSet(AuditedViewSet):
    queryset = Subject.objects.order_by("name")
    serializer_class = SubjectSerializer
    search_fields = ["code", "name"]
    ordering_fields = ["code", "name", "created_at"]


class ClassOfferingViewSet(AuditedViewSet):
    queryset = ClassOffering.objects.select_related("subject").order_by("term", "code")
    serializer_class = ClassOfferingSerializer
    search_fields = ["code", "term", "subject__name"]
    ordering_fields = ["term", "code", "created_at"]


class StudentProfileViewSet(AuditedViewSet):
    queryset = StudentProfile.objects.select_related("user", "course", "class_offering").order_by(
        "ra"
    )
    serializer_class = StudentProfileSerializer
    search_fields = ["ra", "user__first_name", "user__last_name"]
    ordering_fields = ["ra"]


class ProfessorProfileViewSet(AuditedViewSet):
    queryset = (
        ProfessorProfile.objects.select_related("user")
        .prefetch_related("courses", "subjects", "class_offerings")
        .order_by("user__first_name")
    )
    serializer_class = ProfessorProfileSerializer
    search_fields = ["registration", "user__first_name", "user__last_name"]
    ordering_fields = ["registration", "user__first_name"]


class RoomListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AcademicRoomSerializer
    pagination_class = None

    def get_queryset(self):
        professor = require_professor(self.request.user)
        return AcademicRoom.objects.filter(responsible_professor=professor).select_related(
            "responsible_professor__user"
        ).prefetch_related("memberships")

    @transaction.atomic
    def perform_create(self, serializer):
        professor = require_professor(self.request.user)
        room = serializer.save(responsible_professor=professor)
        audit(self.request.user, "CREATE_ROOM", room, ["name", "academic_identifier", "status"])


class RoomDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AcademicRoomSerializer

    def get_object(self):
        return require_owned_room(self.request.user, self.kwargs["room_id"])


class RoomStudentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RoomMembershipSerializer
    pagination_class = None

    def get_queryset(self):
        room = require_owned_room(self.request.user, self.kwargs["room_id"])
        return room.memberships.select_related(
            "student__user", "student__course", "room__responsible_professor__user"
        ).order_by("-is_active", "student__user__first_name", "student__ra")


class EligibleRoomStudentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EligibleRoomStudentSerializer
    pagination_class = None

    def get_queryset(self):
        require_professor(self.request.user)
        query = self.request.query_params.get("q", "").strip()[:100]
        course_id = self.request.query_params.get("course", "").strip()
        if len(query) < 2:
            return StudentProfile.objects.none()
        queryset = (
            StudentProfile.objects.filter(user__is_active=True)
            .filter(
                Q(ra__icontains=query)
                | Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
            )
            .select_related("user", "course")
            .prefetch_related("room_memberships__room__responsible_professor__user")
            .order_by("user__first_name", "user__last_name", "ra")[:10]
        )
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset


class PullRoomStudentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        room = require_owned_room(request.user, room_id)
        student = get_object_or_404(
            StudentProfile.objects.select_related("user"),
            pk=request.data.get("student"),
        )
        membership, transfer = pull_student(actor=request.user, room=room, student=student)
        if transfer:
            return Response(
                RoomTransferRequestSerializer(transfer).data,
                status=status.HTTP_202_ACCEPTED,
            )
        return Response(RoomMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class CloseRoomView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        room = require_owned_room(request.user, room_id)
        return Response(AcademicRoomSerializer(close_room(actor=request.user, room=room)).data)


class MyExpertiseListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfessorExpertiseSerializer
    pagination_class = None

    def get_queryset(self):
        professor = require_professor(self.request.user)
        queryset = ProfessorExpertise.objects.filter(professor=professor)
        query = self.request.query_params.get("q", "").strip()
        if query:
            from .models import normalize_expertise_text
            queryset = queryset.filter(normalized_text__icontains=normalize_expertise_text(query))
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        professor = require_professor(self.request.user)
        try:
            item = serializer.save(professor=professor)
        except IntegrityError as error:
            raise ValidationError("Esta disciplina ou competência já está cadastrada.") from error
        audit(self.request.user, "CREATE_EXPERTISE", item, ["kind", "text", "normalized_text"])


class MyExpertiseDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfessorExpertiseSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        professor = require_professor(self.request.user)
        return ProfessorExpertise.objects.filter(professor=professor)

    @transaction.atomic
    def perform_update(self, serializer):
        try:
            item = serializer.save()
        except IntegrityError as error:
            raise ValidationError("Esta disciplina ou competência já está cadastrada.") from error
        audit(self.request.user, "UPDATE_EXPERTISE", item, serializer.validated_data.keys())

    def perform_destroy(self, instance):
        audit(self.request.user, "DELETE_EXPERTISE", instance, ["kind", "text"])
        instance.delete()


class RoomTransferRequestListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RoomTransferRequestSerializer
    pagination_class = None

    def get_queryset(self):
        if (
            not self.request.user.is_active
            or self.request.user.role not in {"SECRETARIAT", "ADMIN"}
        ):
            raise PermissionDenied("Acesso disponível somente para a secretaria.")
        queryset = RoomTransferRequest.objects.select_related(
            "student__user",
            "source_room__responsible_professor__user",
            "destination_room__responsible_professor__user",
        )
        requested_status = self.request.query_params.get("status", "")
        if requested_status in RoomTransferRequest.Status.values:
            queryset = queryset.filter(status=requested_status)
        return queryset[:100]


class RoomTransferDecisionView(APIView):
    permission_classes = [IsAuthenticated]
    approve = False

    def post(self, request, transfer_id):
        transfer = get_object_or_404(RoomTransferRequest, pk=transfer_id)
        decided = decide_transfer(
            actor=request.user,
            transfer=transfer,
            approve=self.approve,
            note=request.data.get("decision_note", ""),
        )
        return Response(RoomTransferRequestSerializer(decided).data)


class ApproveRoomTransferView(RoomTransferDecisionView):
    approve = True


class DeclineRoomTransferView(RoomTransferDecisionView):
    approve = False


class ProfessorSearchView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        if (
            not self.request.user.is_active
            or self.request.user.role not in {"SECRETARIAT", "ADMIN"}
        ):
            raise PermissionDenied("Área disponível à Secretaria/Admin.")
        query = self.request.query_params.get("q", "").strip()[:100]
        if len(query) < 2:
            return ProfessorProfile.objects.none()
        return (
            ProfessorProfile.objects.filter(user__is_active=True)
            .filter(
                Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(registration__icontains=query)
            )
            .select_related("user")
            .order_by("user__first_name", "user__last_name")[:10]
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(
            [
                {
                    "id": str(profile.pk),
                    "name": profile.user.get_full_name(),
                    "registration": profile.registration,
                }
                for profile in queryset
            ]
        )
