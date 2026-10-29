import io
import secrets

import pytest
from academic.models import AcademicRoom, Enrollment, RoomMembership
from accounts.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from projects.models import Project, ProjectTheme, Publication


@pytest.mark.django_db
def test_e2e_seed_is_idempotent_and_does_not_publish(settings, monkeypatch):
    settings.DEBUG = True
    password = secrets.token_urlsafe(24)
    monkeypatch.setenv("E2E_TEST_PASSWORD", password)
    output = io.StringIO()
    call_command("seed_e2e_acervo", stdout=output)
    assert User.objects.count() == 5
    assert RoomMembership.objects.filter(is_active=True).count() == 2
    assert Enrollment.objects.count() == 2
    assert ProjectTheme.objects.count() == 1
    assert not Project.objects.exists()
    assert not Publication.objects.exists()
    original = User.objects.get(username="ra3001").password
    monkeypatch.setenv("E2E_TEST_PASSWORD", secrets.token_urlsafe(24))
    call_command("seed_e2e_acervo", stdout=output)
    assert User.objects.count() == 5
    assert User.objects.get(username="ra3001").password == original
    call_command("seed_e2e_acervo", reset_test_passwords=True, stdout=output)
    assert User.objects.get(username="ra3001").password != original
    assert password not in output.getvalue()


@pytest.mark.django_db
@pytest.mark.parametrize("command", ["seed_e2e_acervo", "seed_usuarios_teste"])
def test_local_seeds_fail_closed(settings, monkeypatch, command):
    settings.DEBUG = False
    monkeypatch.setenv("E2E_TEST_PASSWORD", secrets.token_urlsafe(24))
    with pytest.raises(CommandError, match="desenvolvimento SQLite"):
        call_command(command)
    settings.DEBUG = True
    monkeypatch.delenv("E2E_TEST_PASSWORD")
    with pytest.raises(CommandError, match="E2E_TEST_PASSWORD"):
        call_command(command)
    assert not User.objects.exists()


@pytest.mark.django_db
def test_e2e_seed_rolls_back_conflicts(settings, monkeypatch):
    settings.DEBUG = True
    monkeypatch.setenv("E2E_TEST_PASSWORD", secrets.token_urlsafe(24))
    call_command("seed_e2e_acervo")
    user = User.objects.get(username="ra3002")
    old_password = user.password
    room = AcademicRoom.objects.get(academic_identifier="SALA-A")
    room.status = AcademicRoom.Status.CLOSED
    room.save(update_fields=["status"])
    with pytest.raises(CommandError, match="Sala de teste conflitante"):
        call_command("seed_e2e_acervo", reset_test_passwords=True)
    user.refresh_from_db()
    assert user.password == old_password


@pytest.mark.django_db
def test_demo_seed_preserves_existing_passwords(settings, monkeypatch):
    settings.DEBUG = True
    monkeypatch.setenv("E2E_TEST_PASSWORD", secrets.token_urlsafe(24))
    output = io.StringIO()
    call_command("seed_usuarios_teste", stdout=output)
    hashes = dict(User.objects.values_list("username", "password"))
    call_command("seed_usuarios_teste", stdout=output)
    assert User.objects.count() == 4
    assert dict(User.objects.values_list("username", "password")) == hashes
