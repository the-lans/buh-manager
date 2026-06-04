from app.config import Settings


def test_parse_comma_separated_emails() -> None:
    s = Settings(_env_file=None, allowed_emails="a@b.com,c@d.com")
    assert s.allowed_emails == ["a@b.com", "c@d.com"]


def test_parse_emails_strips_whitespace() -> None:
    s = Settings(_env_file=None, allowed_emails=" a@b.com , c@d.com ")
    assert s.allowed_emails == ["a@b.com", "c@d.com"]


def test_parse_empty_string_returns_empty_list() -> None:
    s = Settings(_env_file=None, allowed_emails="")
    assert s.allowed_emails == []


def test_list_passthrough() -> None:
    s = Settings(_env_file=None, allowed_emails=["a@b.com"])
    assert s.allowed_emails == ["a@b.com"]


def test_default_is_empty() -> None:
    s = Settings(_env_file=None)
    assert s.allowed_emails == []


def test_parse_single_email() -> None:
    s = Settings(_env_file=None, allowed_emails="only@one.com")
    assert s.allowed_emails == ["only@one.com"]


def test_parse_double_comma_skips_empty_entries() -> None:
    s = Settings(_env_file=None, allowed_emails="a@b.com,,c@d.com")
    assert s.allowed_emails == ["a@b.com", "c@d.com"]


def test_non_local_requires_non_default_secrets() -> None:
    try:
        Settings(_env_file=None, environment="prod")
    except ValueError as exc:
        message = str(exc)
        assert "secret_key" in message
        assert "jwt_secret_key" in message
    else:
        raise AssertionError("Expected non-local settings validation to fail")


def test_non_local_requires_external_integrations() -> None:
    try:
        Settings(
            _env_file=None,
            environment="prod",
            secret_key="prod-secret",
            jwt_secret_key="prod-jwt-secret",
        )
    except ValueError as exc:
        message = str(exc)
        assert "Google OAuth credentials" in message
        assert "Yandex S3 credentials" in message
    else:
        raise AssertionError("Expected non-local integration validation to fail")


def test_non_local_valid_configuration_passes() -> None:
    s = Settings(
        _env_file=None,
        environment="prod",
        secret_key="prod-secret",
        jwt_secret_key="prod-jwt-secret",
        google_client_id="google-client-id",
        google_client_secret="google-client-secret",
        yandex_s3_bucket="bucket",
        yandex_access_key="access-key",
        yandex_secret_key="secret-key",
    )
    assert s.is_local is False
