from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from projects.models import Project, PublicationDocument, Publication


class Command(BaseCommand):
    help = "Cria PublicationDocument + Publication de teste para um projeto"

    def add_arguments(self, parser):
        parser.add_argument('project_id', type=str)
        parser.add_argument('--student', type=str, default='ra3001')

    def handle(self, *args, **options):
        User = get_user_model()
        project = Project.objects.get(pk=options['project_id'])
        student = User.objects.get(username=options['student']).student_profile

        # Criar documento aprovado
        doc = PublicationDocument.objects.create(
            project=project,
            version=1,
            content='Conteúdo do documento E2E.',
            consent_given=True,
            status=PublicationDocument.Status.APPROVED,
            generated_by=student.user,
            reviewed_by=student.user.student_profile if hasattr(student.user, 'student_profile') else None,
            reviewed_at=None,
        )

        # Marcar como aprovado pelo orientador
        prof = User.objects.get(username='prof.teste1').student_profile if hasattr(User.objects.get(username='prof.teste1'), 'student_profile') else None
        # Não tem professor_profile para aluno, usar qualquer professor
        prof_user = User.objects.filter(is_staff=True).first() or User.objects.filter(username='prof.teste1').first()
        if prof_user:
            prof_profile = getattr(prof_user, 'professor_profile', None)
            if prof_profile:
                doc.reviewed_by = prof_profile
                doc.reviewed_at = None
                doc.save()

        # Criar publicação
        publication = Publication.objects.create(
            project=project,
            document=doc,
            published_by_student=student.user,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Publicação criada para projeto {project.id}: publication_id={publication.id}'
        ))
