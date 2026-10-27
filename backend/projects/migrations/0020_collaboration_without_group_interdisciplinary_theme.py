import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0018_add_template_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="projecttheme",
            name="interdisciplinary",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="collaborationopportunity",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="collaboration_opportunities",
                to="projects.projectgroup",
            ),
        ),
    ]
