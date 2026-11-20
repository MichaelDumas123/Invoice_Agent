"""Reusable development CSRF guard; production session binding is not yet implemented."""

from typing import Annotated

from fastapi import Header, HTTPException, Request

from invoice_assistant.config import settings


def validate_csrf(request: Request, token: str | None) -> None:
    origin = request.headers.get("origin")
    if origin and origin not in settings.allowed_origins:
        raise HTTPException(status_code=403, detail="Origin is not allowed")
    if settings.environment == "development" and settings.demo_auth_enabled:
        if token != "local-demo-csrf-token":
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
        return
    raise HTTPException(status_code=403, detail="Production CSRF/session integration is not configured")


def csrf_header(
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> str | None:
    return x_csrf_token
