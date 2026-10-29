import secrets

from scripts.local_environment import load_environment


def test_local_environment_supports_lf_crlf_and_quotes(tmp_path, monkeypatch):
    for key in ("LOCAL_EXAMPLE", "E2E_TEST_PASSWORD", "FORBIDDEN_OVERRIDE"):
        monkeypatch.delenv(key, raising=False)
    value = secrets.token_urlsafe(24)
    (tmp_path / ".env").write_bytes(b"# comment\r\nLOCAL_EXAMPLE='value=with=equals'\r\n")
    (tmp_path / ".env.e2e").write_text(
        f'E2E_TEST_PASSWORD="{value}"\nFORBIDDEN_OVERRIDE=true\n', encoding="utf-8-sig"
    )
    env = load_environment(tmp_path)
    assert env["LOCAL_EXAMPLE"] == "value=with=equals"
    assert env["E2E_TEST_PASSWORD"] == value
    assert "FORBIDDEN_OVERRIDE" not in env
    process_value = secrets.token_urlsafe(24)
    monkeypatch.setenv("E2E_TEST_PASSWORD", process_value)
    assert load_environment(tmp_path)["E2E_TEST_PASSWORD"] == process_value


def test_local_environment_allows_missing_files(tmp_path):
    assert isinstance(load_environment(tmp_path), dict)
