import os

os.environ.setdefault(
    "DJANGO_SECRET_KEY", "test-only-secret-key-with-more-than-fifty-characters-000001"
)
os.environ.setdefault("DATABASE_ENGINE", "sqlite")
