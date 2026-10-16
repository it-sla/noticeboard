from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import admin, auth, directory, email, expiry, notices
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import install_error_handlers


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="Employee Notice Board API",
        docs_url="/api/docs" if s.docs_enabled else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if s.docs_enabled else None,
    )
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        if not request.url.path.startswith("/api/docs"):
            resp.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if request.url.path.startswith("/api/") and request.url.path != "/api/health":
            resp.headers["Cache-Control"] = "no-store"
        if s.cookie_secure:
            resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return resp

    api = APIRouter(prefix="/api")
    for r in (
        auth.router,
        directory.router,
        notices.router,
        email.router,
        admin.router,
        expiry.router,
    ):
        api.include_router(r)

    @api.get("/health", tags=["ops"])
    def health(db: Session = Depends(get_db)):
        db.execute(text("select 1"))
        return {"status": "ok"}

    app.include_router(api)
    return app


app = create_app()
