import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0016_publicationdocument_content'),
    ]

    operations = [
        migrations.AddField(
            model_name='projecttheme',
            name='is_template',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='project',
            name='origin_template',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='projects_from_template', to='projects.projecttheme'),
        ),
    ]
