import pytest
from django.conf import settings


@pytest.mark.unit
def test_secure_defaults():
    assert settings.SESSION_COOKIE_HTTPONLY and settings.CSRF_COOKIE_HTTPONLY
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated"
    ]
