"""Run GF-09/GF-10 with owned local servers; never log credentials.

Requires the existing SQLite fixtures and E2E_TEST_PASSWORD in the environment.
Refuses to reuse listeners: results must come from the current code/configuration.
"""

import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from local_environment import load_environment

ROOT = Path(__file__).resolve().parents[1]


def wait_ready(url, process):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Servidor encerrou antes de ficar disponível.")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:  # noqa: S310
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.2)
    raise TimeoutError("Servidor local não ficou disponível em 30 segundos.")


def main():
    env = load_environment(ROOT)
    if not env.get('E2E_TEST_PASSWORD'):
        raise RuntimeError('Defina E2E_TEST_PASSWORD; nenhuma senha é embutida no runner.')
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Node.js não encontrado no PATH.')
    env.update(DATABASE_ENGINE='sqlite', PYTHONUNBUFFERED='1', VITE_API_BASE_URL='/api/v1')
    for port in (8000, 5173):
        with socket.socket() as connection:
            if connection.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError(f'Porta {port} ocupada; processo existente preservado.')
    processes = []
    with tempfile.TemporaryFile() as server_log:
        try:
            backend = subprocess.Popen(  # noqa: S603
                [sys.executable, 'manage.py',
                 'runserver', '127.0.0.1:8000', '--noreload'],
                cwd=ROOT / 'backend', env=env, stdout=server_log, stderr=server_log,
            )
            processes.append(backend)
            frontend = subprocess.Popen(  # noqa: S603
                [node, 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--strictPort'],
                cwd=ROOT / 'frontend', env=env, stdout=server_log, stderr=server_log,
            )
            processes.append(frontend)
            wait_ready('http://127.0.0.1:8000/api/v1/health/', backend)
            wait_ready('http://127.0.0.1:5173/', frontend)
            return subprocess.run(  # noqa: S603
                [node, 'node_modules/@playwright/test/cli.js', 'test', 'e2e/showcase.spec.ts',
                 '--project=desktop', *sys.argv[1:]],
                cwd=ROOT / 'frontend', env=env, check=False,
            ).returncode
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    sys.exit(main())
