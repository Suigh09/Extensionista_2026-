import pytest
from academic.models import StudentProfile
from accounts.models import LoginAttempt
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


def create_user(username, role, password="Uma-senha-segura-123"):
    return User.objects.create_user(
        username=username, role=role, password=password, first_name="Pessoa"
    )


@pytest.mark.django_db
@pytest.mark.api
@pytest.mark.security
def test_admin_creates_student_without_storing_plain_cpf():
    admin = create_user("admin", User.Role.ADMIN)
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(
        reverse("users"),
        {
            "username": "aluno.01",
            "password": "Senha-segura-2026!",
            "name": "Aluno Teste",
            "role": "STUDENT",
            "ra": "RA1001",
            "cpf": "123.456.789-01",
        },
        format="json",
    )

    assert response.status_code == 201
    profile = StudentProfile.objects.get(ra="RA1001")
    assert profile.cpf_last4 == "8901"
    assert "12345678901" not in profile.cpf_hash
    assert response.json()["profile"]["cpf"] == "***.***.***-8901"


@pytest.mark.django_db
@pytest.mark.security
def test_student_cannot_create_users():
    student = create_user("student", User.Role.STUDENT)
    client = APIClient()
    client.force_authenticate(student)
    response = client.post(reverse("users"), {}, format="json")
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.api
def test_student_logs_in_with_ra_or_cpf():
    admin = create_user("admin", User.Role.ADMIN)
    creator = APIClient()
    creator.force_authenticate(admin)
    creator.post(
        reverse("users"),
        {
            "username": "aluno.02",
            "password": "Senha-segura-2026!",
            "name": "Aluno Dois",
            "role": "STUDENT",
            "ra": "RA2002",
            "cpf": "987.654.321-00",
        },
        format="json",
    )

    for identifier in ["RA2002", "98765432100"]:
        client = APIClient(enforce_csrf_checks=True)
        token = client.get(reverse("csrf")).json()["csrfToken"]
        response = client.post(
            reverse("login"),
            {"identifier": identifier, "password": "Senha-segura-2026!"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 200
        assert response.json()["role"] == "STUDENT"


@pytest.mark.django_db
@pytest.mark.security
def test_login_requires_csrf_and_uses_generic_error():
    client = APIClient(enforce_csrf_checks=True)
    assert (
        client.post(
            reverse("login"), {"identifier": "nobody", "password": "wrong"}, format="json"
        ).status_code
        == 403
    )
    token = client.get(reverse("csrf")).json()["csrfToken"]
    response = client.post(
        reverse("login"),
        {"identifier": "nobody", "password": "wrong"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"] == "Credenciais inválidas ou acesso temporariamente indisponível."
    )


@pytest.mark.django_db
@pytest.mark.regression
def test_logout_invalidates_session():
    create_user("professor", User.Role.PROFESSOR)
    client = APIClient(enforce_csrf_checks=True)
    token = client.get(reverse("csrf")).json()["csrfToken"]
    client.post(
        reverse("login"),
        {"identifier": "professor", "password": "Uma-senha-segura-123"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    token = client.get(reverse("csrf")).json()["csrfToken"]
    assert client.post(reverse("logout"), format="json", HTTP_X_CSRFTOKEN=token).status_code == 204
    assert client.get(reverse("session")).status_code in {401, 403}


@pytest.mark.django_db
@pytest.mark.security
def test_unknown_login_identifiers_do_not_create_persistent_attempts():
    client = APIClient(enforce_csrf_checks=True)
    token = client.get(reverse("csrf")).json()["csrfToken"]
    for number in range(5):
        response = client.post(
            reverse("login"),
            {"identifier": f"inexistente-{number}", "password": "wrong"},
            format="json", HTTP_X_CSRFTOKEN=token, REMOTE_ADDR="192.0.2.10",
        )
        assert response.status_code == 400
    assert LoginAttempt.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.security
def test_login_lock_is_scoped_to_identifier_and_client_address():
    create_user("target", User.Role.PROFESSOR)
    attacker = APIClient(enforce_csrf_checks=True)
    token = attacker.get(reverse("csrf")).json()["csrfToken"]
    for _ in range(5):
        attacker.post(
            reverse("login"), {"identifier": "target", "password": "wrong"},
            format="json", HTTP_X_CSRFTOKEN=token, REMOTE_ADDR="192.0.2.20",
        )
    legitimate = APIClient(enforce_csrf_checks=True)
    legitimate_token = legitimate.get(reverse("csrf")).json()["csrfToken"]
    response = legitimate.post(
        reverse("login"),
        {"identifier": "target", "password": "Uma-senha-segura-123"},
        format="json", HTTP_X_CSRFTOKEN=legitimate_token, REMOTE_ADDR="192.0.2.21",
    )
    assert response.status_code == 200
