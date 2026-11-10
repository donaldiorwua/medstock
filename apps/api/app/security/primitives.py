"""Small, side-effect-free security primitives for milestone A4.1.

This module deliberately does not create database sessions, set cookies, or make HTTP
responses. Those responsibilities belong to later A4 milestones.
"""

import hashlib
import hmac
import secrets
from base64 import urlsafe_b64encode

from argon2 import PasswordHasher, Type
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

# OWASP's minimum recommended Argon2id profile. Keep the parameters explicit so a future
# security review can see exactly what is being used instead of relying on library defaults.
ARGON2_TIME_COST = 2
ARGON2_MEMORY_COST_KIB = 19 * 1024
ARGON2_PARALLELISM = 1
ARGON2_HASH_LENGTH = 32
ARGON2_SALT_LENGTH = 16

_password_hasher = PasswordHasher(
    time_cost=ARGON2_TIME_COST,
    memory_cost=ARGON2_MEMORY_COST_KIB,
    parallelism=ARGON2_PARALLELISM,
    hash_len=ARGON2_HASH_LENGTH,
    salt_len=ARGON2_SALT_LENGTH,
    type=Type.ID,
)

_SESSION_TOKEN_BYTES = 32
_MIN_SESSION_TOKEN_LENGTH = 32
_CSRF_CONTEXT = b"medstock:csrf:v1"


def hash_password(password: str) -> str:
    """Hash a password using Argon2id and a fresh random salt.

    Passwords are intentionally not stripped or normalised: whitespace is part of the
    user's password. The API schema enforces the product's password length policy.
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    try:
        return _password_hasher.hash(password)
    except HashingError as exc:
        raise RuntimeError("Password hashing failed.") from exc


def verify_password(password: str, encoded_hash: str) -> bool:
    """Return whether ``password`` matches an Argon2 encoded hash.

    Malformed or unsupported hashes fail closed and return False. Operational hashing
    failures are not hidden, so callers can distinguish infrastructure failures from
    invalid credentials.
    """
    if not isinstance(password, str) or not password:
        return False
    if not isinstance(encoded_hash, str) or not encoded_hash:
        return False
    try:
        return _password_hasher.verify(encoded_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(encoded_hash: str) -> bool:
    """Report whether a valid hash should be upgraded to the current Argon2id profile."""
    if not isinstance(encoded_hash, str) or not encoded_hash:
        return True
    try:
        return _password_hasher.check_needs_rehash(encoded_hash)
    except (VerificationError, InvalidHashError):
        return True


def generate_session_token() -> str:
    """Generate a cryptographically random bearer token for a browser session."""
    return secrets.token_urlsafe(_SESSION_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Return the lowercase SHA-256 hex digest used by ``UserSession.token_hash``."""
    if not isinstance(token, str) or not token:
        raise ValueError("Token must be a non-empty string.")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token(token: str, expected_hash: str) -> bool:
    """Constant-time comparison of a presented token with its stored SHA-256 digest."""
    if not isinstance(token, str) or not token:
        return False
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        return False
    try:
        int(expected_hash, 16)
    except ValueError:
        return False
    return hmac.compare_digest(hash_token(token), expected_hash.lower())


def generate_csrf_token(session_token: str) -> str:
    """Derive a session-bound CSRF token without storing another secret in the database.

    The raw session token is a high-entropy per-session HMAC key. The returned value is
    deterministic for that session, so a client can obtain it from GET /auth/csrf whenever
    needed. Knowing the CSRF token does not reveal the session token.
    """
    if not isinstance(session_token, str) or len(session_token) < _MIN_SESSION_TOKEN_LENGTH:
        raise ValueError("A sufficiently long session token is required.")
    digest = hmac.new(
        session_token.encode("utf-8"),
        _CSRF_CONTEXT,
        hashlib.sha256,
    ).digest()
    return urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def verify_csrf_token(session_token: str, supplied_token: str) -> bool:
    """Validate a CSRF token against the session token using constant-time comparison."""
    if not isinstance(supplied_token, str) or not supplied_token:
        return False
    try:
        expected = generate_csrf_token(session_token)
    except ValueError:
        return False
    return hmac.compare_digest(expected, supplied_token)
