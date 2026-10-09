import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlmodel import Session

from app.api import assets as assets_api
from app.api import audit as audit_api
from app.api import auth as auth_api
from app.api import categories as categories_api
from app.api import dashboard as dashboard_api
from app.api import depreciation as depreciation_api
from app.api import disposals as disposals_api
from app.api import exports as exports_api
from app.api import imports as imports_api
from app.api import journals as journals_api
from app.api import monthly_reports as monthly_reports_api
from app.api import periods as periods_api
from app.api import reports as reports_api
from app.api import workbooks as workbooks_api
from app.config import settings
from app.database import engine
from app.middleware.errors import register_error_handlers


# Route INFO-level log lines (bootstrap summary, startup messages) to the
# console. Without this, Python's logging default (WARNING) would swallow them.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger("app.main")


def _check_production_safety() -> None:
    """Refuse to start with unsafe configuration when ENVIRONMENT=production."""
    if settings.environment != "production":
        return

    problems: list[str] = []

    placeholder_prefixes = ("replace-me", "CHANGE_ME", "changeme")
    if (
        any(settings.secret_key.startswith(p) for p in placeholder_prefixes)
        or len(settings.secret_key) < 32
    ):
        problems.append(
            "SECRET_KEY is weak or still a placeholder "
            "(must be a random value of at least 32 characters)."
        )

    if not settings.cookie_secure:
        problems.append(
            "COOKIE_SECURE must be true in production "
            "(serve the app over HTTPS and set COOKIE_SECURE=true)."
        )

    if "*" in settings.cors_origins_list:
        problems.append(
            "CORS_ORIGINS must not contain '*' in production. "
            "Set it to the real frontend origin."
        )

    if problems:
        raise RuntimeError(
            "Refusing to start in production with unsafe configuration:\n  - "
            + "\n  - ".join(problems)
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hook.

    On startup, if AUTO_BOOTSTRAP is enabled:
      - ensures tables exist
      - creates the 4 role-based users if missing
      - seeds bank assets if the DB is empty
      - automatically runs monthly depreciation from the latest existing
        record through the current calendar month
      - generates PDF reports for any newly-charged months

    This makes the app self-healing on free-tier hosts where the filesystem
    is wiped between restarts.

    Idempotent: only adds what is missing.
    """
    if settings.auto_bootstrap:
        try:
            from app.services.bootstrap import bootstrap_if_empty
            summary = bootstrap_if_empty()
            logger.info("Bootstrap complete: %s", summary)
        except Exception:
            logger.exception(
                "Bootstrap failed - app will start but may lack data"
            )
    else:
        logger.info("AUTO_BOOTSTRAP disabled - skipping startup seeding")

    yield

    logger.info("Shutting down")


def create_app() -> FastAPI:
    _check_production_safety()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # Central error handling - sanitized responses, no stack traces
    register_error_handlers(app)

    @app.get("/api/health")
    def health():
        """Liveness probe: the process is up."""
        return {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment,
        }

    @app.get("/api/health/ready")
    def readiness():
        """Readiness probe: the process AND the database are healthy."""
        try:
            with Session(engine) as db:
                db.exec(text("SELECT 1"))
            return {"status": "ok", "db": "ok"}
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"status": "degraded", "db": "unreachable"},
            )

    # M1
    app.include_router(auth_api.router)

    # M2
    app.include_router(categories_api.router)
    app.include_router(assets_api.router)

    # M3
    app.include_router(depreciation_api.router)

    # M4
    app.include_router(workbooks_api.router)

    # M5
    app.include_router(disposals_api.router)
    app.include_router(journals_api.router)
    app.include_router(reports_api.router)
    app.include_router(dashboard_api.router)
    app.include_router(audit_api.router)
    app.include_router(periods_api.router)

    # M6
    app.include_router(exports_api.router)
    app.include_router(imports_api.router)

    # v3.0 - monthly reports (bank-style schedule, download/print)
    app.include_router(monthly_reports_api.router)

    return app


app = create_app()