import pytest

from app.services.deduplication import compute_file_hash


@pytest.mark.parametrize(
    "data, expected_equal",
    [
        (b"hello world", True),
        (b"", True),
    ],
)
def test_same_bytes_produce_same_hash(data: bytes, expected_equal: bool) -> None:
    assert (compute_file_hash(data) == compute_file_hash(data)) is expected_equal


@pytest.mark.parametrize(
    "a, b",
    [
        (b"abc", b"ABC"),
        (b"hello", b"world"),
        (b"data1", b"data2"),
        (b"", b" "),
    ],
)
def test_different_bytes_produce_different_hash(a: bytes, b: bytes) -> None:
    assert compute_file_hash(a) != compute_file_hash(b)


def test_hash_is_hex_string() -> None:
    h = compute_file_hash(b"test")
    assert isinstance(h, str)
    assert all(c in "0123456789abcdef" for c in h)


def test_empty_bytes_has_known_sha256() -> None:
    # SHA-256 of empty bytes is a well-known constant
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert compute_file_hash(b"") == expected
