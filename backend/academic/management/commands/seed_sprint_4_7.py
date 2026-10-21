from django.core.management.base import BaseCommand
from django.db import transaction

from academic.models import (
    AcademicRoom,
    ProfessorExpertise,
    ProfessorProfile,
    RoomMembership,
    StudentProfile,
    normalize_expertise_text,
)


class Command(BaseCommand):
    help = "Cria de forma idempotente os dados locais de validação da Sprint 4.7."

    @transaction.atomic
    def handle(self, *args, **options):
        professor1 = ProfessorProfile.objects.select_related("user").filter(
            user__username="professor1", user__is_active=True
        ).first()
        professor2 = ProfessorProfile.objects.select_related("user").filter(
            user__username="professor2", user__is_active=True
        ).first()
        if not professor1 or not professor2:
            self.stdout.write(self.style.WARNING(
                "professor1/professor2 não encontrados; contas não foram recriadas."
            ))
            return

        room, _ = AcademicRoom.objects.get_or_create(
            responsible_professor=professor1,
            name="Sala de Projetos Extensionistas",
            defaults={"academic_identifier": "Validação Sprint 4.7"},
        )
        for username in ("aluno1", "aluno2"):
            student = StudentProfile.objects.select_related("user").filter(
                user__username=username, user__is_active=True
            ).first()
            if (
                student
                and not RoomMembership.objects.filter(
                    student=student, is_active=True
                ).exists()
            ):
                RoomMembership.objects.create(
                    room=room, student=student, assigned_by=professor1.user
                )

        expertise = {
            professor1: [
                (ProfessorExpertise.Kind.DISCIPLINE, "Desenvolvimento Web"),
                (ProfessorExpertise.Kind.COMPETENCY, "Tecnologia"),
            ],
            professor2: [
                (ProfessorExpertise.Kind.DISCIPLINE, "Enfermagem"),
                (ProfessorExpertise.Kind.COMPETENCY, "Saúde"),
            ],
        }
        for professor, items in expertise.items():
            for kind, text in items:
                ProfessorExpertise.objects.get_or_create(
                    professor=professor,
                    kind=kind,
                    normalized_text=normalize_expertise_text(text),
                    defaults={"text": text},
                )
        self.stdout.write(self.style.SUCCESS("Dados da Sprint 4.7 preparados."))
