"""Internal notification helper (kinds consumed by the Sprint 8 central)."""

from .models import Notification


def notify(users, kind, title, body="", project=None):
    if not isinstance(users, list | tuple | set):
        users = [users]
    targets = [user for user in users if user is not None and user.is_active]
    if not targets:
        return []
    return Notification.objects.bulk_create(
        [
            Notification(
                user=user,
                kind=kind,
                title=str(title)[:160],
                body=str(body or "")[:500],
                project=project,
            )
            for user in targets
        ]
    )


def institutional_staff():
    from .models import User

    return list(
        User.objects.filter(
            is_active=True, role__in=[User.Role.SECRETARIAT, User.Role.ADMIN]
        )
    )
