"""Carregamento local sem impressão de valores ou dependências extras."""

import os
from pathlib import Path


def load_environment(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    for name in (".env", ".env.e2e"):
        path = root / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            # O arquivo de teste só pode fornecer credenciais dos testes locais.
            if name == ".env.e2e" and key != "E2E_TEST_PASSWORD":
                continue
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            env.setdefault(key, value)
    return env
