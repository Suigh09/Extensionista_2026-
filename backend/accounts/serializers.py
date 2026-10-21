from academic.models import ProfessorProfile, StudentProfile
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import AuditEvent, Notification, User, cpf_fingerprint, normalize_digits


class ProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="get_full_name")
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "name", "email", "role", "profile"]

    def get_profile(self, user):
        if user.role == User.Role.STUDENT and hasattr(user, "student_profile"):
            profile = user.student_profile
            offering = profile.class_offering
            enrollments = profile.enrollments.filter(is_active=True).select_related(
                "class_offering__subject"
            ).prefetch_related("class_offering__professorprofile_set__user")
            from projects.models import ProjectGroup

            project_groups = (
                ProjectGroup.objects.filter(
                    members__student=profile,
                    members__is_active=True,
                    is_active=True,
                    project__is_active=True,
                )
                .select_related(
                    "project", "responsible_professor__user", "evaluator__user"
                )
                .prefetch_related("members__student__user")
                .distinct()
            )
            room_membership = profile.room_memberships.filter(is_active=True).select_related(
                "room__responsible_professor__user"
            ).first()
            return {
                "ra": profile.ra,
                "cpf": f"***.***.***-{profile.cpf_last4}",
                "course": (
                    {"code": profile.course.code, "name": profile.course.name}
                    if profile.course
                    else None
                ),
                "class_offering": str(offering.pk) if offering else None,
                "class_offering_label": (
                    f"{offering.code} · {offering.term}" if offering else None
                ),
                "current_term": offering.term if offering else None,
                "enrollments": [
                    {
                        "id": str(enrollment.pk),
                        "subject_code": enrollment.class_offering.subject.code,
                        "subject_name": enrollment.class_offering.subject.name,
                        "offering_code": enrollment.class_offering.code,
                        "term": enrollment.class_offering.term,
                        "professors": [
                            professor.user.get_full_name() or professor.user.username
                            for professor in enrollment.class_offering.professorprofile_set.all()
                            if professor.user.is_active
                        ],
                    }
                    for enrollment in enrollments
                ],
                "projects": [
                    {
                        "id": str(group.project_id),
                        "name": group.project.name,
                        "status": group.project.status,
                        "advisor": (
                            group.responsible_professor.user.get_full_name()
                            or group.responsible_professor.user.username
                            if group.responsible_professor
                            else None
                        ),
                        "evaluator": (
                            group.evaluator.user.get_full_name() or group.evaluator.user.username
                            if group.evaluator
                            else None
                        ),
                        "members": [
                            member.student.user.get_full_name() or member.student.user.username
                            for member in group.members.all()
                            if member.is_active
                        ],
                    }
                    for group in project_groups
                ],
                "active_room": (
                    {
                        "id": str(room_membership.room_id),
                        "name": room_membership.room.name,
                        "academic_identifier": room_membership.room.academic_identifier,
                        "professor_name": (
                            room_membership.room.responsible_professor.user.get_full_name()
                        )
                        or room_membership.room.responsible_professor.user.username,
                    }
                    if room_membership
                    else None
                ),
            }
        if user.role == User.Role.PROFESSOR and hasattr(user, "professor_profile"):
            profile = user.professor_profile
            offerings = profile.class_offerings.select_related("subject").filter(is_active=True)
            return {
                "registration": profile.registration,
                "courses": list(profile.courses.filter(is_active=True).values("code", "name")),
                "subjects": list(profile.subjects.filter(is_active=True).values("code", "name")),
                "class_offerings": [
                    {
                        "id": str(offering.pk),
                        "label": f"{offering.subject.name} · {offering.code} · {offering.term}",
                        "subject_name": offering.subject.name,
                        "offering_code": offering.code,
                        "term": offering.term,
                        "student_count": offering.enrollments.filter(is_active=True).count(),
                    }
                    for offering in offerings
                ],
                "advising_projects": [
                    {
                        "id": str(group.project_id),
                        "name": group.project.name,
                        "status": group.project.status,
                    }
                    for group in profile.responsible_project_groups.filter(
                        is_active=True, project__is_active=True
                    ).select_related("project")
                ],
                "evaluating_projects": [
                    {
                        "id": str(group.project_id),
                        "name": group.project.name,
                        "status": group.project.status,
                    }
                    for group in profile.evaluated_project_groups.filter(
                        is_active=True, project__is_active=True
                    ).select_related("project")
                ],
                "expertise": [
                    {
                        "id": str(item.pk),
                        "kind": item.kind,
                        "text": item.text,
                        "normalized_text": item.normalized_text,
                    }
                    for item in profile.expertise_items.all()
                ],
                "rooms": [
                    {
                        "id": str(room.pk),
                        "name": room.name,
                        "academic_identifier": room.academic_identifier,
                        "status": room.status,
                        "student_count": room.memberships.filter(is_active=True).count(),
                    }
                    for room in profile.academic_rooms.all()
                ],
            }
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    name = serializers.CharField(write_only=True)
    ra = serializers.CharField(write_only=True, required=False)
    cpf = serializers.CharField(write_only=True, required=False)
    registration = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "name",
            "email",
            "role",
            "ra",
            "cpf",
            "registration",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        role = attrs["role"]
        if role == User.Role.STUDENT and (not attrs.get("ra") or not attrs.get("cpf")):
            raise serializers.ValidationError("Aluno exige RA e CPF.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        name = validated_data.pop("name").strip().split(maxsplit=1)
        ra = validated_data.pop("ra", "")
        cpf = validated_data.pop("cpf", "")
        registration = validated_data.pop("registration", "")
        password = validated_data.pop("password")
        user = User(
            **validated_data, first_name=name[0], last_name=name[1] if len(name) > 1 else ""
        )
        user.set_password(password)
        user.save()
        if user.role == User.Role.STUDENT:
            digits = normalize_digits(cpf)
            StudentProfile.objects.create(
                user=user,
                ra=ra.strip().upper(),
                cpf_hash=cpf_fingerprint(digits),
                cpf_last4=digits[-4:],
            )
        elif user.role == User.Role.PROFESSOR:
            ProfessorProfile.objects.create(user=user, registration=registration.strip())
        AuditEvent.objects.create(
            actor=self.context["request"].user,
            action="CREATE",
            object_type="accounts.User",
            object_id=str(user.pk),
            changed_fields=["username", "name", "email", "role"],
        )
        return user


class NotificationSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)

    class Meta:
        model = Notification
        fields = [
            "id",
            "kind",
            "title",
            "body",
            "project",
            "project_name",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields
