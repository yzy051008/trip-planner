"""Request trace ID helpers."""

import secrets


def new_trace_id() -> str:
    return secrets.token_hex(6)
