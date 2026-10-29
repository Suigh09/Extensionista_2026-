"""Prepara fixtures locais existentes; não aplica migrações nem remove dados."""

import subprocess
import sys
from pathlib import Path

from local_environment import load_environment

ROOT = Path(__file__).resolve().parents[1]


def main():
    env = load_environment(ROOT)
    env.update(DATABASE_ENGINE="sqlite", DJANGO_ENV="development")
    return subprocess.run(  # noqa: S603
        [sys.executable, "manage.py", "seed_e2e_acervo",
         *sys.argv[1:]],
        cwd=ROOT / "backend", env=env, check=False,
    ).returncode


if __name__ == "__main__":
    sys.exit(main())
