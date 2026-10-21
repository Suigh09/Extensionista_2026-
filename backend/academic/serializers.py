from rest_framework import serializers

from .models import (
    AcademicRoom,
    ClassOffering,
    Course,
    ProfessorExpertise,
    ProfessorProfile,
    RoomMembership,
    RoomTransferRequest,
    StudentProfile,
    Subject,
)


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "code", "name", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "code", "name", "workload_hours", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ClassOfferingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassOffering
        fields = ["id", "subject", "term", "code", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.get_full_name", read_only=True)
    login = serializers.CharField(source="user.username", read_only=True)
    cpf = serializers.SerializerMethodField()
    active_room = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = ["user", "name", "login", "ra", "cpf", "course", "class_offering", "active_room"]
        read_only_fields = ["user", "ra", "cpf"]

    def get_cpf(self, profile):
        return f"***.***.***-{profile.cpf_last4}"

    def get_active_room(self, profile):
        membership = profile.room_memberships.filter(is_active=True).select_related(
            "room__responsible_professor__user"
        ).first()
        return RoomMembershipSerializer(membership).data if membership else None


class ProfessorProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.get_full_name", read_only=True)
    login = serializers.CharField(source="user.username", read_only=True)
    expertise = serializers.SerializerMethodField()
    rooms = serializers.SerializerMethodField()

    class Meta:
        model = ProfessorProfile
        fields = [
            "user",
            "name",
            "login",
            "registration",
            "courses",
            "subjects",
            "class_offerings",
            "expertise",
            "rooms",
        ]
        read_only_fields = ["user"]

    def get_expertise(self, profile):
        return ProfessorExpertiseSerializer(profile.expertise_items.all(), many=True).data

    def get_rooms(self, profile):
        return AcademicRoomSerializer(profile.academic_rooms.all(), many=True).data


class AcademicRoomSerializer(serializers.ModelSerializer):
    responsible_professor_name = serializers.CharField(
        source="responsible_professor.user.get_full_name", read_only=True
    )
    professor_name = serializers.CharField(
        source="responsible_professor.user.get_full_name", read_only=True
    )
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = AcademicRoom
        fields = [
            "id",
            "name",
            "academic_identifier",
            "responsible_professor_name",
            "professor_name",
            "status",
            "student_count",
            "created_at",
            "updated_at",
            "closed_at",
        ]
        read_only_fields = [
            "id",
            "responsible_professor_name",
            "professor_name",
            "status",
            "student_count",
            "created_at",
            "updated_at",
            "closed_at",
        ]

    def get_student_count(self, room):
        return room.memberships.filter(is_active=True).count()

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Informe o nome da sala.")
        return value


class RoomMembershipSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source="room.name", read_only=True)
    professor_name = serializers.CharField(
        source="room.responsible_professor.user.get_full_name", read_only=True
    )
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_ra = serializers.CharField(source="student.ra", read_only=True)
    name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    ra = serializers.CharField(source="student.ra", read_only=True)
    course_name = serializers.CharField(source="student.course.name", read_only=True, default=None)

    class Meta:
        model = RoomMembership
        fields = [
            "id",
            "room",
            "room_name",
            "professor_name",
            "student",
            "student_name",
            "student_ra",
            "name",
            "ra",
            "course_name",
            "joined_at",
            "left_at",
            "is_active",
        ]
        read_only_fields = fields


class EligibleRoomStudentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.get_full_name", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True, default=None)
    active_room = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = ["id", "name", "ra", "course_name", "active_room"]

    def get_active_room(self, profile):
        membership = profile.room_memberships.filter(is_active=True).select_related(
            "room__responsible_professor__user"
        ).first()
        if not membership:
            return None
        return {
            "id": str(membership.room_id),
            "name": membership.room.name,
            "professor_name": membership.room.responsible_professor.user.get_full_name()
                or membership.room.responsible_professor.user.username,
        }


class ProfessorExpertiseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessorExpertise
        fields = ["id", "kind", "text", "normalized_text", "created_at", "updated_at"]
        read_only_fields = ["id", "normalized_text", "created_at", "updated_at"]

    def validate_text(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Informe a disciplina ou competência.")
        return value


class RoomTransferRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_ra = serializers.CharField(source="student.ra", read_only=True)
    source_room_name = serializers.CharField(source="source_room.name", read_only=True)
    destination_room_name = serializers.CharField(source="destination_room.name", read_only=True)
    source_professor_name = serializers.CharField(
        source="source_room.responsible_professor.user.get_full_name", read_only=True
    )
    destination_professor_name = serializers.CharField(
        source="destination_room.responsible_professor.user.get_full_name",
        read_only=True,
    )

    class Meta:
        model = RoomTransferRequest
        fields = [
            "id",
            "student",
            "student_name",
            "student_ra",
            "source_room",
            "source_room_name",
            "source_professor_name",
            "destination_room",
            "destination_room_name",
            "destination_professor_name",
            "status",
            "created_at",
            "decided_at",
            "decision_note",
        ]
        read_only_fields = fields
