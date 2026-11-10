"""Pure-ASGI middleware that gives every request an ID and echoes it in X-Request-Id."""

import re
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

HEADER = "X-Request-Id"
# Only accept caller-supplied IDs that are boring: protects logs from injected junk.
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def _pick_request_id(scope: Scope) -> str:
    supplied = Headers(scope=scope).get(HEADER)
    if supplied and _SAFE_ID.fullmatch(supplied):
        return supplied
    return uuid.uuid4().hex


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _pick_request_id(scope)
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[HEADER] = request_id
            await send(message)

        await self.app(scope, receive, send_with_request_id)
