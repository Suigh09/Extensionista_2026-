"""Servidor de teste PostgreSQL descartável; usado somente pelo runner integrado."""

import hashlib
import os
import re
import signal
import tempfile
from datetime import timedelta

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
        raise RuntimeError("Somente PostgreSQL isolado.")
    original = connection.settings_dict["NAME"]
    name = os.environ["ACERVO_TEST_DB_NAME"]
    if not re.fullmatch(r"test_acervo_live_[a-f0-9]{32}", name):
        raise RuntimeError("Nome de base de teste inválido.")
    admin = psycopg.connect(**connection.get_connection_params(), autocommit=True)
    created = False

    def stop(*args):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    with tempfile.TemporaryDirectory(prefix="acervo-live-") as media:
        try:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            created = True
            connections.close_all()
            settings.DATABASES["default"]["NAME"] = name
            connection.settings_dict["NAME"] = name
            settings.MEDIA_ROOT = media
            call_command("migrate", verbosity=0, interactive=False)
            seed()
            call_command("runserver", "0.0.0.0:8000", use_reloader=False, verbosity=0)
        finally:
            connections.close_all()
            settings.DATABASES["default"]["NAME"] = original
            connection.settings_dict["NAME"] = original
            if created:
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
            admin.close()


def seed():
    from academic.models import ClassOffering, ProfessorProfile, StudentProfile, Subject
    from accounts.models import User
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.utils import timezone
    from projects.deliveries import forward_project, review_delivery, submit_delivery
    from projects.models import GroupMember, Project, ProjectGroup
    from projects.showcase import create_showcase_entry

    password = os.environ.get("E2E_TEST_PASSWORD")
    if not password:
        raise RuntimeError("Senha de testes não fornecida pelo runner.")
    users = {}
    for role, key in [
        ("ADMIN", "secretary"),
        ("PROFESSOR", "advisor"),
        ("PROFESSOR", "evaluator"),
        ("STUDENT", "leader"),
    ]:
        users[key] = User.objects.create_user(
            username=f"live-{key}", role=role, first_name=f"Teste {key}", password=password
        )
    advisor = ProfessorProfile.objects.create(user=users["advisor"], registration="LIVE-A")
    evaluator = ProfessorProfile.objects.create(user=users["evaluator"], registration="LIVE-E")
    student = StudentProfile.objects.create(
        user=users["leader"],
        ra="LIVE-LEADER",
        cpf_hash=hashlib.sha256(b"live-synthetic").hexdigest(),
        cpf_last4="0000",
    )
    subject = Subject.objects.create(code="LIVE", name="Extensão")
    offering = ClassOffering.objects.create(subject=subject, code="LIVE", term="2026.2")
    for index, suffix in enumerate(
        ("desktop-direct", "desktop-corrected", "mobile-direct", "mobile-corrected")
    ):
        project = Project.objects.create(
            name=f"Acervo Integrado {suffix}",
            about="Teste isolado",
            class_offering=offering,
            status="APPROVED",
            created_by=users["leader"],
        )
        group = ProjectGroup.objects.create(
            project=project,
            class_offering=offering,
            leader=student,
            responsible_professor=advisor,
            evaluator=evaluator,
            name=f"Grupo {suffix}",
        )
        GroupMember.objects.create(group=group, student=student)
        delivery = submit_delivery(
            actor=users["leader"],
            project=project,
            uploaded=SimpleUploadedFile(
                "entrega.pdf", b"%PDF-1.4\nTeste\n%%EOF", content_type="application/pdf"
            ),
        )
        review_delivery(actor=users["advisor"], delivery=delivery, decision="APPROVED")
        forward_project(actor=users["advisor"], project=project)
        create_showcase_entry(
            actor=users["secretary"],
            group=group,
            date=timezone.now() + timedelta(hours=index + 1),
            location="Sala de teste",
        )


if __name__ == "__main__":
    main()
