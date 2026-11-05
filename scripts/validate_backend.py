"""Runner local de pytest com configuração isolada, sem usar o banco da plataforma."""

import os
import sys
from pathlib import Path

from local_environment import load_environment


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "backend"))
    os.environ.update(load_environment(root))
    os.environ["DATABASE_ENGINE"] = "sqlite"
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    os.chdir(root)
    import pytest

    return pytest.main(sys.argv[1:] or ["--cov", "-q"])


if __name__ == "__main__":
    sys.exit(main())
