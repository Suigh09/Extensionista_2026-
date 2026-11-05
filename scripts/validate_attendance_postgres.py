"""Valida presença/nota concorrentes em base PostgreSQL descartável, sem copiar dados."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
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
    database = "test_attendance_" + uuid.uuid4().hex
    admin = psycopg.connect(**connection.get_connection_params(), autocommit=True)
    created = False
    try:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
        created = True
        connections.close_all()
        settings.DATABASES["default"]["NAME"] = database
        connection.settings_dict["NAME"] = database
        call_command("migrate", verbosity=0, interactive=False)

        from academic.models import ClassOffering, ProfessorProfile, StudentProfile, Subject
        from accounts.models import User
        from django.utils import timezone
        from projects.grading import group_grade_value, submit_direct_grade
        from projects.models import (
            GradeSubmission,
            GroupMember,
            Project,
            ProjectGroup,
            ShowcaseEntry,
        )
        from projects.showcase import record_member_attendance

        actor = User.objects.create_user(username="temporary-evaluator", role="PROFESSOR")
        professor, _ = ProfessorProfile.objects.get_or_create(user=actor)
        subject = Subject.objects.create(code="TEMP", name="Temporária")
        offering = ClassOffering.objects.create(subject=subject, term="2026.2", code="TEMP")
        project = Project.objects.create(
            name="Temporário",
            about="Teste",
            created_by=actor,
            class_offering=offering,
            status="APPROVED",
        )
        group = ProjectGroup.objects.create(
            project=project, class_offering=offering, evaluator=professor
        )
        user = User.objects.create_user(username="temporary-student", role="STUDENT")
        student, _ = StudentProfile.objects.get_or_create(user=user, defaults={"ra": "TEMP"})
        member = GroupMember.objects.create(group=group, student=student)
        entry = ShowcaseEntry.objects.create(
            group=group, date=timezone.now(), location="Teste", status="SCHEDULED"
        )
        barrier = Barrier(2)

        def record(_):
            try:
                barrier.wait(timeout=15)
                return record_member_attendance(
                    actor=actor,
                    entry=entry,
                    member_attendances=[{"member_id": member.pk, "present": True}],
                ).status
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert list(pool.map(record, range(2))) == ["PRESENTED", "PRESENTED"]
        assert entry.member_attendances.count() == 1
        barrier = Barrier(2)

        def grade(_):
            try:
                barrier.wait(timeout=15)
                return submit_direct_grade(
                    actor=actor, entry=entry, value="8.75", comment="Teste"
                ).pk
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(grade, range(2)))
        assert results[0] == results[1]
        assert GradeSubmission.objects.count() == 1
        assert str(group_grade_value(group)[0]) == "8.75"
        print("PostgreSQL: presença e avaliação concorrentes idempotentes, sem duplicação.")
    finally:
        connections.close_all()
        settings.DATABASES["default"]["NAME"] = original
        connection.settings_dict["NAME"] = original
        if created:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database)))
        admin.close()


if __name__ == "__main__":
    main()
