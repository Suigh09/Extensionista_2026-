"""Orquestra UI/API reais em PostgreSQL descartável, sem atos no banco normal."""

import http.client
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

from local_environment import load_environment


def main():
    root = Path(__file__).resolve().parents[1]
    env = load_environment(root)
    if not env.get("E2E_TEST_PASSWORD"):
        raise RuntimeError("Credencial local de testes ausente.")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8002)) == 0:
            raise RuntimeError("Porta 8002 ocupada. Processo existente preservado.")
    name = "acervo-live-" + uuid.uuid4().hex[:12]
    docker = shutil.which("docker")
    npx = shutil.which("npx.cmd")
    if not docker or not npx:
        raise RuntimeError("Docker e npm são necessários.")
    log = root / ".runtime" / f"{name}.log"
    env["ACERVO_LIVE_API"] = "http://127.0.0.1:8002/api/v1"
    database = "test_acervo_live_" + uuid.uuid4().hex
    env["ACERVO_TEST_DB_NAME"] = database
    process = None
    with log.open("w", encoding="utf-8") as output:
        try:
            process = subprocess.Popen(  # noqa: S603 - executável local e argumentos fixos/UUID.
                [
                    docker,
                    "compose",
                    "run",
                    "--rm",
                    "--no-deps",
                    "-T",
                    "--name",
                    name,
                    "-e",
                    "E2E_TEST_PASSWORD",
                    "-e",
                    "ACERVO_TEST_DB_NAME",
                    "-p",
                    "127.0.0.1:8002:8000",
                    "backend",
                    "python",
                    "-",
                ],
                cwd=root,
                env=env,
                stdin=subprocess.PIPE,
                stdout=output,
                stderr=output,
            )
            process.stdin.write((root / "scripts" / "serve_acervo_e2e.py").read_bytes())
            process.stdin.close()
            for _ in range(90):
                if process.poll() is not None:
                    raise RuntimeError(f"Servidor de teste encerrou. Consulte {log.name}.")
                try:
                    health = http.client.HTTPConnection("127.0.0.1", 8002, timeout=2)
                    health.request("GET", "/api/v1/health/")
                    response = health.getresponse()
                    if response.status == 200:
                        break
                except (OSError, http.client.HTTPException):
                    time.sleep(1)
                finally:
                    health.close()
            else:
                raise RuntimeError("Servidor de teste não ficou pronto no prazo.")
            result = subprocess.run(  # noqa: S603 - comando fixo de testes local.
                [npx, "playwright", "test", "--config=playwright.acervo-live.config.ts"],
                cwd=root / "frontend",
                env=env,
                check=False,
            )
            return result.returncode
        finally:
            if process:
                subprocess.run(  # noqa: S603 - somente container criado com UUID nesta execução.
                    [docker, "stop", "--timeout", "15", name],
                    cwd=root,
                    stdout=output,
                    stderr=output,
                    check=False,
                )
                process.wait(timeout=30)
                # A proteção externa também funciona se o servidor falhar antes do finally.
                cleanup = (
                    "import os,psycopg; from psycopg import sql; "
                    "c=psycopg.connect(dbname=os.environ['POSTGRES_DB'], "
                    "user=os.environ['POSTGRES_USER'],password=os.environ['POSTGRES_PASSWORD'], "
                    "host=os.environ['POSTGRES_HOST'],autocommit=True); "
                    "c.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)')"
                    f".format(sql.Identifier('{database}'))); "
                    "c.close(); print('Base descartavel removida.')"
                )
                subprocess.run(  # noqa: S603 - nome UUID desta execução, SQL com Identifier.
                    [docker, "compose", "exec", "-T", "backend", "python", "-c", cleanup],
                    cwd=root,
                    env=env,
                    check=True,
                )


if __name__ == "__main__":
    sys.exit(main())
