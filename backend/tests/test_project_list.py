import pytest
from accounts.models import User
from projects.models import Project
from rest_framework.test import APIClient

from .test_projects import academic_context  # noqa: F401


@pytest.mark.django_db
def test_admin_list_includes_inactive_and_paginates_at_most_100(academic_context):  # noqa: F811
    offering, _, student = academic_context
    user, _, student_client = student(1)
    Project.objects.bulk_create([
        Project(
            number=number,
            name=f"Projeto {number:03}",
            about="Projeto de teste",
            class_offering=offering,
            created_by=user,
            is_active=number != 101,
        )
        for number in range(1, 102)
    ])
    admin = User.objects.create_user(username="list-admin", role="ADMIN")
    client = APIClient()
    client.force_authenticate(admin)
    url = "/api/v1/projects/institutional/"
    response = client.get(url, {"page_size": 500, "ordering": "name"})
    assert response.status_code == 200
    assert response.data["count"] == 101
    assert len(response.data["results"]) == 100
    second = client.get(url, {"page": 2, "ordering": "name"})
    assert [row["number"] for row in second.data["results"]] == [101]
    filtered = client.get(url, {"search": "Projeto 101"})
    assert filtered.data["count"] == 1
    assert student_client.get(url).status_code == 403
