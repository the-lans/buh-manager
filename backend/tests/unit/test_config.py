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
