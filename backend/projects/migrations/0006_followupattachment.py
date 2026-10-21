import django.db.models.deletion
import projects.models
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0005_project_approval_and_about")]
    operations = [
        migrations.CreateModel(
            name="FollowUpAttachment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("file", models.FileField(max_length=300, upload_to=projects.models.follow_up_attachment_path)),
                ("original_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=120)),
                ("size", models.PositiveBigIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("follow_up", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attachments", to="projects.followup")),
            ],
            options={"ordering": ["created_at", "id"]},
        )
    ]
