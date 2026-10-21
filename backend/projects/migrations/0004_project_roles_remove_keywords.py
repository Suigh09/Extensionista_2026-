from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("projects", "0003_collaborationopportunity_collaborationapplication_and_more")]
    operations = [
        migrations.RemoveField(model_name="project", name="keywords"),
        migrations.AddField(
            model_name="projectgroup", name="responsible_professor",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="responsible_project_groups", to="academic.professorprofile"),
        ),
        migrations.AddField(
            model_name="projectgroup", name="evaluator",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="evaluated_project_groups", to="academic.professorprofile"),
        ),
    ]
