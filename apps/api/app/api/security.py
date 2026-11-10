"""Security schemes as the contract describes them (blueprint 5.2).

Until milestone A4 these only DESCRIBE the requirements in OpenAPI (auto_error=False means
they never reject a request). A4 adds the real checks behind the same scheme names, so
the contract does not change when authentication is implemented.
"""

from fastapi import Depends
from fastapi.security import APIKeyCookie, APIKeyHeader

SESSION_COOKIE_NAME = "medstock_session"
CSRF_HEADER_NAME = "X-CSRF-Token"

session_cookie = APIKeyCookie(
    name=SESSION_COOKIE_NAME,
    scheme_name="sessionCookie",
    description="Server-side session cookie set by POST /auth/login (HttpOnly, Secure).",
    auto_error=False,
)
csrf_header = APIKeyHeader(
    name=CSRF_HEADER_NAME,
    scheme_name="csrfToken",
    description="CSRF token from GET /auth/csrf. Required on every mutating request.",
    auto_error=False,
)

# Reads need a session. Writes need a session and the CSRF header.
READ_AUTH = [Depends(session_cookie)]
WRITE_AUTH = [Depends(session_cookie), Depends(csrf_header)]
