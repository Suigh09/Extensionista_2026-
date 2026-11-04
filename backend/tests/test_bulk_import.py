import csv
import io

import pytest
from academic.models import (
    AcademicRoom,
    ClassOffering,
    Course,
    ProfessorProfile,
    StudentProfile,
    Subject,
)
from accounts.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def admin_user():
    return User.objects.create_user(
        username="admin.import",
        role=User.Role.ADMIN,
        password="Admin-senha-segura-123!",
        is_active=True,
    )


@pytest.fixture
def course_and_offering(db):
    course = Course.objects.create(code="ADS", name="Análise de Sistemas", is_active=True)
    subject = Subject.objects.create(
        code="ADS101",
        name="Fundamentos",
        workload_hours=60,
        is_active=True,
    )
    offering = ClassOffering.objects.create(
        subject=subject, term="2026.2", code="ADS-2026.2", is_active=True
    )
    room = AcademicRoom.objects.create(
        academic_identifier="SALA-TEST",
        name="Sala Teste",
        status="ACTIVE",
        responsible_professor=ProfessorProfile.objects.create(user=User.objects.create_user(
            username="prof.room", role=User.Role.PROFESSOR, password="x", is_active=True
        )),
    )
    return course, offering, room


@pytest.fixture
def api_client(admin_user):
    client = APIClient(enforce_csrf_checks=True)
    client.force_authenticate(admin_user)
    return client


def make_csv(rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[
        "username", "role", "first_name", "last_name", "email",
        "password", "ra", "course_code", "class_offering_code", "registration",
    ])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return SimpleUploadedFile(
        "usuarios.csv",
        buffer.getvalue().encode("utf-8"),
        content_type="text/csv",
    )


@pytest.mark.django_db
@pytest.mark.security
def test_bulk_import_creates_students_and_professors(api_client, course_and_offering):
    course, offering, _ = course_and_offering
    file = make_csv([
        {
            "username": "aluno.bulk01",
            "role": "STUDENT",
            "first_name": "Ana",
            "last_name": "Bulk",
            "email": "ana.bulk@exemplo.local",
            "password": "Senha-segura-2026!",
            "ra": "ADB001",
            "course_code": course.code,
            "class_offering_code": offering.code,
            "registration": "",
        },
        {
            "username": "prof.bulk01",
            "role": "PROFESSOR",
            "first_name": "Bruno",
            "last_name": "Bulk",
            "email": "bruno.bulk@exemplo.local",
            "password": "Senha-segura-2026!",
            "ra": "",
            "course_code": "",
            "class_offering_code": "",
            "registration": "PROF-B001",
        },
    ])

    response = api_client.post("/api/v1/auth/users/import-csv/", {"file": file}, format="multipart")

    assert response.status_code == status.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["created"] == 2
    assert data["errors"] == 0
    assert data["success"] is True

    assert User.objects.filter(username="aluno.bulk01").exists()
    assert User.objects.filter(username="prof.bulk01").exists()

    aluno = User.objects.get(username="aluno.bulk01")
    assert aluno.role == User.Role.STUDENT
    assert aluno.student_profile.ra == "ADB001"
    assert aluno.student_profile.course == course
    assert aluno.student_profile.class_offering == offering

    prof = User.objects.get(username="prof.bulk01")
    assert prof.role == User.Role.PROFESSOR
    assert prof.professor_profile.registration == "PROF-B001"


@pytest.mark.django_db
@pytest.mark.security
def test_bulk_import_rejects_duplicates(api_client, course_and_offering):
    course, offering, _ = course_and_offering
    # Usuário já existente
    User.objects.create_user(
        username="aluno.dup",
        role=User.Role.STUDENT,
        password="Senha-segura-2026!",
        is_active=True,
    )
    StudentProfile.objects.create(
        user=User.objects.get(username="aluno.dup"),
        ra="ADU001",
        course=course,
        class_offering=offering,
    )

    file = make_csv([
        {
            "username": "aluno.dup",
            "role": "STUDENT",
            "first_name": "Ana",
            "last_name": "Dup",
            "email": "ana.dup@exemplo.local",
            "password": "Senha-segura-2026!",
            "ra": "ADU001",
            "course_code": course.code,
            "class_offering_code": offering.code,
            "registration": "",
        },
    ])

    response = api_client.post("/api/v1/auth/users/import-csv/", {"file": file}, format="multipart")

    assert response.status_code == status.HTTP_207_MULTI_STATUS
    data = response.json()
    assert data["created"] == 0
    assert data["errors"] >= 1
    assert data["success"] is False
    assert any("já existe" in e["message"] for e in data["error_details"])


@pytest.mark.django_db
@pytest.mark.security
def test_bulk_import_rejects_invalid_course(api_client, course_and_offering):
    course, offering, _ = course_and_offering
    file = make_csv([
        {
            "username": "aluno.bad",
            "role": "STUDENT",
            "first_name": "Ana",
            "last_name": "Bad",
            "email": "ana.bad@exemplo.local",
            "password": "Senha-segura-2026!",
            "ra": "ADB002",
            "course_code": "INEXISTENTE",
            "class_offering_code": offering.code,
            "registration": "",
        },
    ])

    response = api_client.post("/api/v1/auth/users/import-csv/", {"file": file}, format="multipart")

    assert response.status_code == status.HTTP_207_MULTI_STATUS
    data = response.json()
    assert data["created"] == 0
    assert data["errors"] == 1
    assert "não encontrado" in data["error_details"][0]["message"]


@pytest.mark.django_db
@pytest.mark.security
def test_bulk_import_requires_admin(api_client):
    # Remover permissão de admin e usar usuário comum
    student = User.objects.create_user(
        username="student.noadmin",
        role=User.Role.STUDENT,
        password="Senha-segura-2026!",
        is_active=True,
    )
    client = APIClient(enforce_csrf_checks=True)
    client.force_authenticate(student)

    file = make_csv([
        {
            "username": "aluno.x",
            "role": "STUDENT",
            "first_name": "X",
            "last_name": "Y",
            "email": "x.y@exemplo.local",
            "password": "Senha-segura-2026!",
            "ra": "ADX001",
            "course_code": "ADS",
            "class_offering_code": "ADS-2026.2",
            "registration": "",
        },
    ])

    response = client.post("/api/v1/auth/users/import-csv/", {"file": file}, format="multipart")
    assert response.status_code == status.HTTP_403_FORBIDDEN
