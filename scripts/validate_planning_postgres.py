"""Run inside the backend container; create/drop only a unique disposable test DB.

No application rows or credentials are copied. Requires CREATE DATABASE permission.
Validates real PostgreSQL row locks, which SQLite cannot exercise.
"""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
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

    original_name = settings.DATABASES["default"]["NAME"]
    connection = connections["default"]
    if connection.vendor != "postgresql":
        raise RuntimeError("Este teste exige PostgreSQL, não SQLite.")
    params = connection.get_connection_params()
    database = "test_planning_" + uuid.uuid4().hex
    admin = psycopg.connect(**params, autocommit=True)
    created = False
    try:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
        created = True
        connections.close_all()
        settings.DATABASES["default"]["NAME"] = database
        connection.settings_dict["NAME"] = database
        call_command("migrate", verbosity=0, interactive=False)

        from academic.models import ClassOffering, ProfessorProfile, Subject
        from accounts.models import User
        from projects.evaluation import designate_evaluator
        from projects.grading import submit_grades
        from projects.models import (
            Criterion,
            Project,
            ProjectForwarding,
            ProjectGroup,
            Rubric,
            ShowcaseBuilding,
            ShowcaseDay,
            ShowcaseEntry,
            ShowcaseRoom,
        )
        from projects.planning import schedule_group
        from rest_framework.exceptions import PermissionDenied, ValidationError

        actor = User.objects.create_user(username="temporary-secretary", role="SECRETARIAT")
        subject = Subject.objects.create(code="TEMP", name="Extensão temporária")
        offering = ClassOffering.objects.create(subject=subject, term="2026.2", code="TEMP")

        def new_project(index):
            try:
                project = Project.objects.create(
                    name=f"Temporário {index}",
                    about="Teste isolado",
                    class_offering=offering,
                    created_by=actor,
                    status="APPROVED",
                )
                return project.pk, project.number
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=8) as pool:
            projects = list(pool.map(new_project, range(8)))
        numbers = [number for _, number in projects]
        assert sorted(numbers) == list(range(1, 9)), "Números concorrentes inválidos"
        groups = []
        for identity, _ in projects[:2]:
            ProjectForwarding.objects.create(project_id=identity, forwarded_by=actor)
            groups.append(ProjectGroup.objects.create(project_id=identity, class_offering=offering))
        building = ShowcaseBuilding.objects.create(number=1, code="A", name="Prédio A")
        room = ShowcaseRoom.objects.create(building=building, number=1, name="Sala 1")
        day = ShowcaseDay.objects.create(
            date=date(2026, 12, 10), start_time=time(8), end_time=time(18)
        )
        barrier = Barrier(2)

        def reserve(group):
            try:
                barrier.wait(timeout=10)
                schedule_group(
                    actor=actor,
                    data={
                        "group": group.pk,
                        "day": day.pk,
                        "room": room.pk,
                        "start_time": time(9),
                        "end_time": time(10),
                    },
                )
                return "saved"
            except ValidationError:
                return "conflict"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(reserve, groups))
        assert sorted(outcomes) == ["conflict", "saved"], outcomes
        assert ShowcaseEntry.objects.count() == 1
        print("OK: PostgreSQL real — 8 números concorrentes únicos; colisão de sala bloqueada.")
        print("OK: números de projeto concorrentes; colisão de sala bloqueada.")

    finally:
        connections.close_all()
        settings.DATABASES["default"]["NAME"] = original_name
        connection.settings_dict["NAME"] = original_name
        if created:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database)))
        admin.close()
        print("Banco de teste descartável encerrado; banco da plataforma preservado.")


if __name__ == "__main__":
    main()