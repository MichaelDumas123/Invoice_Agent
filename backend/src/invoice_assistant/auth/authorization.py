"""Demo identity and authorization boundaries.

Production deployment must replace the development identity adapter with an
approved OIDC-backed server session. Authorization remains enforced server-side.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from invoice_assistant.api.schemas import Role
from invoice_assistant.config import settings


@dataclass(frozen=True)
class Principal:
    user_id: str
    workspace_id: str
    role: Role


def authenticate_session(authorization: str | None = None) -> Principal:
    """Production placeholder. A configured OIDC verifier must replace this fail-closed path."""
    from invoice_assistant.config import settings

    if settings.environment == "development" and settings.demo_auth_enabled:
        raise RuntimeError("Use the development-only demo header dependency in development")
    if not authorization:
        raise HTTPException(status_code=401, detail="Authenticated OIDC session is required")
    raise HTTPException(status_code=503, detail="OIDC session verification is not configured")


def get_principal(
    x_demo_user: Annotated[str | None, Header()] = None,
    x_demo_workspace: Annotated[str | None, Header()] = None,
    x_demo_role: Annotated[str | None, Header()] = None,
) -> Principal:
    """Accept only explicitly enabled demo identity; never use in production."""
    if not settings.demo_auth_enabled or settings.environment != "development":
        raise HTTPException(status_code=401, detail="Authenticated session required; OIDC verification is not configured")
    if not x_demo_user or not x_demo_workspace or not x_demo_role:
        raise HTTPException(status_code=401, detail="Demo identity headers required")
    try:
        role = Role(x_demo_role)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Unknown role") from exc
    return Principal(user_id=x_demo_user, workspace_id=x_demo_workspace, role=role)


def require_role(*allowed: Role):
    def dependency(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(status_code=403, detail="Role is not authorized for this action")
        return principal

    return dependency


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
