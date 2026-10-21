import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("academic", "0002_initial")]
    operations = [
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(default=True)),
                ("enrolled_at", models.DateTimeField(auto_now_add=True)),
                ("class_offering", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="enrollments", to="academic.classoffering")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="enrollments", to="academic.studentprofile")),
            ],
            options={
                "indexes": [models.Index(fields=["student", "is_active"], name="academic_en_student_cb76ea_idx")],
                "constraints": [models.UniqueConstraint(fields=("student", "class_offering"), name="unique_student_enrollment")],
            },
        )
    ]
