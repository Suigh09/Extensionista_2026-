"""Fluxos do acervo e concorrência em base descartável, sem copiar dados reais.

Executar via stdin no container backend. Remove somente a base única criada aqui.
"""

import hashlib
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import django
import psycopg
from psycopg import sql


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connections

    connection = connections["default"]
    if connection.vendor != "postgresql":
        raise RuntimeError("Exige PostgreSQL.")
    original = connection.settings_dict["NAME"]
    original_media = settings.MEDIA_ROOT
    database = "test_publication_" + uuid.uuid4().hex
    admin = psycopg.connect(**connection.get_connection_params(), autocommit=True)
    created = False
    with tempfile.TemporaryDirectory(prefix="acervo-validation-") as media:
        try:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
            created = True
            connections.close_all()
            settings.DATABASES["default"]["NAME"] = database
            connection.settings_dict["NAME"] = database
            settings.MEDIA_ROOT = media
            call_command("migrate", verbosity=0, interactive=False)
            run_flows()
        finally:
            connections.close_all()
            settings.DATABASES["default"]["NAME"] = original
            connection.settings_dict["NAME"] = original
            settings.MEDIA_ROOT = original_media
            if created:
                admin.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database))
                )
            admin.close()


def run_flows():
    from academic.models import ClassOffering, ProfessorProfile, StudentProfile, Subject
    from accounts.models import User
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.db import connections
    from django.utils import timezone
    from projects.deliveries import forward_project, review_delivery, submit_delivery
    from projects.grading import submit_direct_grade
    from projects.models import GroupMember, Project, ProjectGroup, Publication, PublicationDocument
    from projects.publication_workflow import confirm_publication, decide_document, submit_document
    from projects.showcase import create_showcase_entry, record_member_attendance
    from rest_framework.exceptions import ValidationError

    secretary = User.objects.create_user(username="temporary-secretary", role="ADMIN")
    advisor = User.objects.create_user(username="temporary-advisor", role="PROFESSOR")
    advisor_profile = ProfessorProfile.objects.create(user=advisor, registration="TEMP-A")
    evaluator = User.objects.create_user(username="temporary-evaluator", role="PROFESSOR")
    evaluator_profile = ProfessorProfile.objects.create(user=evaluator, registration="TEMP-E")
    subject = Subject.objects.create(code="TEMP", name="Temporária")
    offering = ClassOffering.objects.create(subject=subject, term="2026.2", code="TEMP")
    for corrected in (False, True):
        leader = User.objects.create_user(username=f"temporary-leader-{corrected}", role="STUDENT")
        student = StudentProfile.objects.create(
            user=leader,
            ra=f"TEMP-{corrected}",
            cpf_hash=hashlib.sha256(f"synthetic-{corrected}".encode()).hexdigest(),
            cpf_last4="0000",
        )
        project = Project.objects.create(
            name=f"Temporário {corrected}",
            about="Teste isolado",
            class_offering=offering,
            status="APPROVED",
            created_by=leader,
        )
        group = ProjectGroup.objects.create(
            project=project,
            class_offering=offering,
            leader=student,
            responsible_professor=advisor_profile,
            evaluator=evaluator_profile,
        )
        member = GroupMember.objects.create(group=group, student=student)
        upload = SimpleUploadedFile(
            "entrega.pdf", b"%PDF-1.4\nTeste\n%%EOF", content_type="application/pdf"
        )
        delivery = submit_delivery(actor=leader, project=project, uploaded=upload)
        review_delivery(actor=advisor, delivery=delivery, decision="APPROVED")
        forward_project(actor=advisor, project=project)
        entry = create_showcase_entry(
            actor=secretary,
            group=group,
            date=timezone.now() + timedelta(hours=2 if corrected else 1),
            location="Teste",
        )
        record_member_attendance(
            actor=evaluator,
            entry=entry,
            member_attendances=[{"member_id": member.pk, "present": True}],
        )
        submit_direct_grade(actor=evaluator, entry=entry, value="8.75", comment="Teste")
        barrier = Barrier(2)

        def submit(_, gate=barrier, user=leader, project_id=project.pk):
            try:
                gate.wait(timeout=15)
                doc = submit_document(
                    actor=user,
                    project_id=project_id,
                    expected_document=None,
                    title="Título de extensão",
                    abstract="Resumo com acentos.",
                    content="Texto com inclusão e ação.",
                    consent=True,
                )
                return str(doc.pk)
            except ValidationError:
                return "stale"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(submit, range(2)))
        assert outcomes.count("stale") == 1, outcomes
        first = PublicationDocument.objects.get(project=project)
        with first.pdf.open("rb") as file:
            assert hashlib.sha256(file.read()).hexdigest() == first.pdf_sha256
        if corrected:
            second = decide_document(
                actor=advisor,
                project_id=project.pk,
                expected_document=first.pk,
                action="correct",
                title=first.title,
                abstract=first.abstract,
                content="Texto corrigido.",
            )
            try:
                confirm_publication(
                    actor=secretary, project_id=project.pk, expected_document=second.pk
                )
            except ValidationError:
                pass
            else:
                raise AssertionError("Publicou sem aceite do líder")
            decide_document(
                actor=leader, project_id=project.pk, expected_document=second.pk, action="accept"
            )
            current = second
        else:
            decide_document(
                actor=advisor, project_id=project.pk, expected_document=first.pk, action="approve"
            )
            current = first
        barrier = Barrier(2)

        def publish(_, gate=barrier, project_id=project.pk, document_id=current.pk):
            try:
                gate.wait(timeout=15)
                confirm_publication(
                    actor=secretary, project_id=project_id, expected_document=document_id
                )
                return "published"
            except ValidationError:
                return "blocked"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(publish, range(2)))
        assert sorted(outcomes) == ["blocked", "published"], outcomes
        publication = Publication.objects.get(project=project)
        assert publication.document_id == current.pk
        assert publication.confirmed_by_id == secretary.pk
        assert PublicationDocument.objects.filter(project=project).count() == (
            2 if corrected else 1
        )
        first.refresh_from_db()
        assert first.content == "Texto com inclusão e ação."
    print("PostgreSQL: ambos os fluxos aprovados; concorrência sem duplicar versões/publicações.")


if __name__ == "__main__":
    main()
