"""Usuários demonstrativos, restritos ao desenvolvimento local."""

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User


class Command(BaseCommand):
    help = "Cria usuários demonstrativos sem alterar senhas existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG or settings.DATABASES["default"]["ENGINE"] != (
            "django.db.backends.sqlite3"
        ):
            raise CommandError("Permitido somente em desenvolvimento SQLite.")
        password = os.environ.get("E2E_TEST_PASSWORD", "")
        if len(password) < 16:
            raise CommandError("Defina E2E_TEST_PASSWORD com pelo menos 16 caracteres.")
        created_count = 0
        for username, role in (
            ("admin", User.Role.ADMIN),
            ("professor", User.Role.PROFESSOR),
            ("secretaria", User.Role.SECRETARIAT),
            ("aluno", User.Role.STUDENT),
        ):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"role": role, "first_name": "Demonstração", "last_name": "Local"},
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
                created_count += 1
        self.stdout.write(f"Usuários demonstrativos criados: {created_count}; senha não exibida.")
