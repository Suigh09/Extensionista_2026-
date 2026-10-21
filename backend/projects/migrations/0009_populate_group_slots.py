from django.db import migrations


def populate(apps, schema_editor):
    Member = apps.get_model("projects", "GroupMember")
    Slot = apps.get_model("projects", "ActiveGroupSlot")
    Group = apps.get_model("projects", "ProjectGroup")
    for group in Group.objects.all().iterator():
        first = Member.objects.filter(group=group, is_active=True).order_by("joined_at", "pk").first()
        if first:
            group.leader_id = first.student_id
            group.save(update_fields=["leader"])
    occupied = {}
    for member in Member.objects.filter(is_active=True, group__is_active=True, group__project__is_active=True).exclude(group__project__status__in=["COMPLETED", "ARCHIVED", "CANCELLED"]).iterator():
        if member.student_id in occupied:
            raise RuntimeError("Migração interrompida: existe aluno em mais de um grupo vigente. Regularize os vínculos antes de continuar.")
        occupied[member.student_id] = member.group_id
    Slot.objects.bulk_create([Slot(student_id=student_id, group_id=group_id) for student_id, group_id in occupied.items()])


class Migration(migrations.Migration):
    dependencies = [("projects", "0008_themes_and_lifecycle")]
    operations = [migrations.RunPython(populate, migrations.RunPython.noop)]
