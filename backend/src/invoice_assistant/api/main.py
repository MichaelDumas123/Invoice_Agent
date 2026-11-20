"""FastAPI app factory for the invoice assistant."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from invoice_assistant.api.routes import router
from invoice_assistant.config import settings
from invoice_assistant.observability.metrics import metrics


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield

    app = FastAPI(
        title="Accounts-Payable Invoice Assistant API",
        version="0.1.0",
        description="Development MVP uses synthetic extraction only; no invoice payment or approval.",
        max_body_size=settings.max_upload_bytes + 1024 * 1024,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "X-Demo-User", "X-Demo-Workspace", "X-Demo-Role", "X-CSRF-Token", "Idempotency-Key"],
    )
    @app.middleware("http")
    async def request_id_middleware(request, call_next):
        import secrets

        request_id = request.headers.get("X-Request-ID") or secrets.token_hex(12)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        metrics.increment("http_requests_total", {"route": request.url.path.split("/")[-1] or "root", "method": request.method, "status": str(response.status_code)})
        return response
    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'")
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    app.include_router(router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "synthetic-demo"}

    @app.get("/internal/metrics", tags=["health"])
    def read_metrics() -> dict[str, object]:
        if settings.environment != "development":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        return {"metrics": metrics.snapshot()}

    return app


app = create_app()
