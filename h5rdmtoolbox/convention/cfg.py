from contextvars import ContextVar
from typing import Optional

_current_convention: ContextVar[Optional["Convention"]] = ContextVar(
    "current_convention", default=None
)
_registered_conventions: dict = {}
