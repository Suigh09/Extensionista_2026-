import pytest
from django.urls import reverse


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.django_db
def test_health_contract(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api", "version": "0.1.0"}


@pytest.mark.security
@pytest.mark.regression
@pytest.mark.django_db
def test_health_does_not_disclose_configuration(client):
    payload = client.get(reverse("health")).json()
    assert {"database", "host", "secret", "password", "debug"}.isdisjoint(payload)


@pytest.mark.security
@pytest.mark.django_db
def test_security_headers(client):
    response = client.get(reverse("health"))
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"
