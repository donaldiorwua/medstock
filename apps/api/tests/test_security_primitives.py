import re

import pytest

from app.security.primitives import (
    generate_csrf_token,
    generate_session_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_csrf_token,
    verify_password,
    verify_token,
)


def test_password_hash_uses_argon2id_and_random_salt() -> None:
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")

    assert first.startswith("$argon2id$")
    assert second.startswith("$argon2id$")
    assert first != second


def test_password_verification_accepts_correct_and_rejects_wrong_password() -> None:
    encoded = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", encoded) is True
    assert verify_password("incorrect password", encoded) is False


def test_password_verification_fails_closed_for_empty_or_malformed_inputs() -> None:
    assert verify_password("", "not-a-hash") is False
    assert verify_password("password", "not-a-hash") is False
    assert verify_password("password", "") is False


def test_hash_password_rejects_empty_password() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        hash_password("")


def test_password_rehash_check_accepts_current_hash() -> None:
    assert password_needs_rehash(hash_password("a sufficiently long password")) is False
    assert password_needs_rehash("malformed") is True


def test_session_tokens_are_random_urlsafe_and_sufficiently_long() -> None:
    first = generate_session_token()
    second = generate_session_token()

    assert first != second
    assert len(first) >= 40
    assert re.fullmatch(r"[A-Za-z0-9_-]+", first)


def test_session_token_hash_matches_database_column_contract() -> None:
    token = generate_session_token()
    digest = hash_token(token)

    assert len(digest) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert verify_token(token, digest) is True
    assert verify_token("different-token", digest) is False


def test_token_verification_fails_closed_for_invalid_hashes() -> None:
    assert verify_token("some-token", "") is False
    assert verify_token("some-token", "not-a-sha256-digest") is False
    assert verify_token("", "a" * 64) is False


def test_csrf_token_is_stable_and_bound_to_one_session() -> None:
    session_token = generate_session_token()
    other_session_token = generate_session_token()

    csrf_token = generate_csrf_token(session_token)

    assert csrf_token == generate_csrf_token(session_token)
    assert csrf_token != generate_csrf_token(other_session_token)
    assert verify_csrf_token(session_token, csrf_token) is True
    assert verify_csrf_token(other_session_token, csrf_token) is False


def test_csrf_verification_rejects_tampered_or_missing_tokens() -> None:
    session_token = generate_session_token()
    csrf_token = generate_csrf_token(session_token)

    assert verify_csrf_token(session_token, csrf_token + "x") is False
    assert verify_csrf_token(session_token, "") is False
    assert verify_csrf_token("short", csrf_token) is False


def test_csrf_generation_rejects_short_session_tokens() -> None:
    with pytest.raises(ValueError, match="sufficiently long"):
        generate_csrf_token("short")
