"""Converte usuários com role SECRETARIAT para ADMIN, unificando os perfis."""

from django.db import migrations


def convert_secretariat_to_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="SECRETARIAT").update(role="ADMIN")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_publication_workflow"),
    ]

    operations = [
        migrations.RunPython(convert_secretariat_to_admin, migrations.RunPython.noop),
    ]
