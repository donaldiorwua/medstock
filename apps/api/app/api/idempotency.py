from typing import Annotated

from fastapi import Header

# Declared as a REQUIRED header so generated clients must send it. A missing header is
# answered with IDEMPOTENCY_KEY_REQUIRED (see core/errors.py), not a generic 422.
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
        description=(
            "A unique value (a UUID is ideal) chosen by the client for this action. "
            "Repeating the same key with the same body returns the original result "
            "without acting twice."
        ),
    ),
]
