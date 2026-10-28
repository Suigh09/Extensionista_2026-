from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from projects.models import Project, PublicationDocument, Publication


class Command(BaseCommand):
    help = "Cria PublicationDocument aprovado + Publicação para um projeto de teste E2E"

    def add_arguments(self, parser):
        parser.add_argument('project_id', type=str)
        parser.add_argument('--student', type=str, default='ra3001')

    def handle(self, *args, **options):
        User = get_user_model()
        project = Project.objects.get(pk=options['project_id'])
        student = User.objects.get(username=options['student']).student_profile

        # Criar documento aprovado (sem arquivo físico, apenas conteúdo)
        doc = PublicationDocument.objects.create(
            project=project,
            version=1,
            content='Conteúdo do documento E2E.',
            consent_given=True,
            status=PublicationDocument.Status.APPROVED,
            generated_by=student.user,
        )

        # Criar publicação
        publication = Publication.objects.create(
            project=project,
            document=doc,
            published_by_student=student.user,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Publicação criada para projeto {project.id}: publication_id={publication.id}'
        ))
