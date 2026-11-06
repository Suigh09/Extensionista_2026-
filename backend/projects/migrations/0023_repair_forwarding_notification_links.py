from collections import defaultdict

from django.db import migrations


def repair_links(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Notification = apps.get_model("accounts", "Notification")
    database = schema_editor.connection.alias
    matches = defaultdict(list)
    for identity, name in Project.objects.using(database).values_list("pk", "name"):
        matches[f"Encaminhamento recebido de {name}"[:160]].append(identity)
    notifications = Notification.objects.using(database).filter(
        kind="PROJECT_FORWARDED",
        project__isnull=True,
        user__role__in=["ADMIN"],
    )
    for item in notifications.iterator():
        candidates = matches.get(item.title, [])
        # No fuzzy matching, no guess when titles (including truncated titles) collide.
        if len(candidates) == 1:
            item.project_id = candidates[0]
            item.save(using=database, update_fields=["project"])


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0022_showcase_planning"),
        ("accounts", "0006_alter_notification_kind"),
    ]
    operations = [migrations.RunPython(repair_links, migrations.RunPython.noop)]
