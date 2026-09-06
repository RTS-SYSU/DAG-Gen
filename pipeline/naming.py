from __future__ import annotations

import re

from .errors import ValidationError

NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


def validate_name(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{field} must be non-empty string")
    if NAME_RE.match(value) is None:
        raise ValidationError(f"{field}='{value}' must match [A-Za-z0-9_]+")
    return value

