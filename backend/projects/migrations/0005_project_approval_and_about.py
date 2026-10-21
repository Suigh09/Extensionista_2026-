from django.db import migrations, models
import django.db.models.deletion


def copy_about(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    for project in Project.objects.all().iterator():
        project.about = project.scope.strip() or project.description.strip()
        project.save(update_fields=["about"])


class Migration(migrations.Migration):
    dependencies = [("projects", "0004_project_roles_remove_keywords")]
    operations = [
        migrations.AddField(model_name="project", name="about", field=models.TextField(default=""), preserve_default=False),
        migrations.RunPython(copy_about, migrations.RunPython.noop),
        migrations.RemoveField(model_name="project", name="description"),
        migrations.RemoveField(model_name="project", name="scope"),
        migrations.AlterField(
            model_name="project", name="status",
            field=models.CharField(choices=[("DRAFT", "Rascunho"), ("PENDING_APPROVAL", "Aguardando aprovação"), ("CHANGES_REQUESTED", "Ajustes solicitados"), ("APPROVED", "Aprovado"), ("COMPLETED", "Concluído"), ("ARCHIVED", "Arquivado")], default="DRAFT", max_length=20),
        ),
        migrations.AddField(model_name="project", name="submitted_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="project", name="reviewed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="project", name="review_feedback", field=models.TextField(blank=True, max_length=2000)),
        migrations.AddField(
            model_name="project", name="reviewed_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_projects", to="academic.professorprofile"),
        ),
    ]
