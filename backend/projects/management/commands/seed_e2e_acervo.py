"""Fixtures sintéticas locais para GF-09/GF-10, sem publicações artificiais."""

import hashlib
import os

from academic.models import (
    AcademicRoom,
    ClassOffering,
    Course,
    Enrollment,
    ProfessorExpertise,
    ProfessorProfile,
    RoomMembership,
    StudentProfile,
    Subject,
)
from accounts.models import User
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from projects.models import ProjectTheme


class Command(BaseCommand):
    help = "Prepara fixtures E2E somente em desenvolvimento SQLite; preserva dados existentes."

    def add_arguments(self, parser):
        parser.add_argument("--reset-test-passwords", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG or settings.DATABASES["default"]["ENGINE"] != (
            "django.db.backends.sqlite3"
        ):
            raise CommandError("Fixtures E2E permitidas somente em desenvolvimento SQLite.")
        password = os.environ.get("E2E_TEST_PASSWORD", "")
        if len(password) < 16:
            raise CommandError("Defina E2E_TEST_PASSWORD com pelo menos 16 caracteres.")
        users = {}
        for username, role in (
            ("ra3001", User.Role.STUDENT),
            ("ra3002", User.Role.STUDENT),
            ("prof.teste1", User.Role.PROFESSOR),
            ("secretaria.teste", User.Role.SECRETARIAT),
            ("avaliador.e2e.acervo", User.Role.PROFESSOR),
        ):
            user, created = User.objects.get_or_create(
                username=username, defaults={"role": role, "is_active": True}
            )
            if user.role != role or not user.is_active:
                raise CommandError("Usuário de teste conflitante; nenhuma alteração confirmada.")
            if created or options["reset_test_passwords"]:
                user.set_password(password)
                user.save(update_fields=["password"])
            users[username] = user
        course, _ = Course.objects.get_or_create(code="E2E", defaults={"name": "Curso E2E"})
        subject, _ = Subject.objects.get_or_create(
            code="EXT101", defaults={"name": "Projetos de Extensão", "workload_hours": 60}
        )
        offering, _ = ClassOffering.objects.get_or_create(
            subject=subject, term="2026.2", code="EXT101-E2E"
        )
        advisor, _ = ProfessorProfile.objects.get_or_create(user=users["prof.teste1"])
        evaluator, _ = ProfessorProfile.objects.get_or_create(user=users["avaliador.e2e.acervo"])
        evaluator.user.first_name = "Avaliador"
        evaluator.user.last_name = "E2E Acervo"
        evaluator.user.save(update_fields=["first_name", "last_name"])
        for professor in (advisor, evaluator):
            professor.courses.add(course)
            professor.subjects.add(subject)
            professor.class_offerings.add(offering)
        ProfessorExpertise.objects.get_or_create(
            professor=evaluator,
            kind=ProfessorExpertise.Kind.COMPETENCY,
            normalized_text="extensao",
            defaults={"text": "Extensão"},
        )
        room, _ = AcademicRoom.objects.get_or_create(
            academic_identifier="SALA-A",
            defaults={"name": "Sala A", "responsible_professor": advisor},
        )
        if room.responsible_professor_id != advisor.pk or room.status != AcademicRoom.Status.ACTIVE:
            raise CommandError("Sala de teste conflitante; nenhuma alteração confirmada.")
        for username in ("ra3001", "ra3002"):
            profile, _ = StudentProfile.objects.get_or_create(
                user=users[username],
                defaults={
                    "ra": username.upper(), "course": course, "class_offering": offering,
                    "cpf_hash": hashlib.sha256(f"synthetic-e2e-{username}".encode()).hexdigest(),
                    "cpf_last4": "0000",
                },
            )
            if profile.course_id != course.pk or profile.class_offering_id != offering.pk:
                raise CommandError("Matrícula de teste conflitante; nenhuma alteração confirmada.")
            active = RoomMembership.objects.filter(student=profile, is_active=True).first()
            if active and active.room_id != room.pk:
                raise CommandError("Vínculo de teste conflitante; nenhuma alteração confirmada.")
            if not active:
                RoomMembership.objects.create(student=profile, room=room, assigned_by=advisor.user)
            Enrollment.objects.get_or_create(student=profile, class_offering=offering)
        ProjectTheme.objects.get_or_create(
            room=room, title="Sala A", defaults={"description": "Tema sintético E2E"}
        )
        self.stdout.write(self.style.SUCCESS("Fixtures E2E preparadas; senha não exibida."))
