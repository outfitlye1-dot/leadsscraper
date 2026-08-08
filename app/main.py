from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.database.base import Base
from app.database.database import engine
from app.database.migrate import (
    ensure_brain_columns,
    ensure_conversation_columns,
    ensure_lead_columns,
    ensure_outreach_settings_columns,
    ensure_user_google_columns,
    ensure_whatsapp_chat_columns,
)
from app.routes import admin, ai, auth, brain, campaigns, cv, dashboard, email_outreach, leads, messages, payments, scraper, settings as settings_routes, support, user_api_keys, whatsapp_chat, whatsapp_web, whatsapp_webhook
from app.utils.file_utils import ensure_directory


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    import logging
    import threading

    settings = get_settings()
    if settings.SECRET_KEY == "change-me-in-production-use-a-long-random-string":
        logging.getLogger(__name__).warning(
            "SECRET_KEY is still the default — set a strong random value in .env before production"
        )
    ensure_directory(settings.UPLOAD_DIR)
    ensure_directory(settings.EXPORT_DIR)
    import app.models  # noqa: F401 — register all ORM tables

    Base.metadata.create_all(bind=engine)
    ensure_lead_columns(engine)
    ensure_outreach_settings_columns(engine)
    ensure_user_google_columns(engine)
    ensure_brain_columns(engine)
    ensure_conversation_columns(engine)
    ensure_whatsapp_chat_columns(engine)
    from app.database.database import SessionLocal
    from app.database.admin_bootstrap import ensure_admin_user

    with SessionLocal() as db:
        ensure_admin_user(db)
    # Defer outreach worker so login/API are responsive immediately after startup
    import threading

    def _start_worker():
        from app.services.email_outreach.worker import outreach_worker

        outreach_worker.start()
        settings = get_settings()
        if settings.WA_WEB_ENABLED and settings.WA_WEB_AUTO_START_WORKER:
            from app.services.whatsapp_web.worker import wa_web_worker

            wa_web_worker.start()

    threading.Timer(3.0, _start_worker).start()
    yield
    from app.services.email_outreach.worker import outreach_worker

    outreach_worker.stop()
    try:
        from app.services.whatsapp_web.worker import wa_web_worker

        wa_web_worker.stop()
    except Exception:
        pass
    try:
        from app.services.whatsapp_web.browser import wa_web_browser

        # Shutdown must not run on the asyncio loop thread (Playwright Sync)
        await asyncio.to_thread(wa_web_browser.shutdown)
    except Exception:
        pass


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-powered Lead Generation SaaS Backend API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_origin_regex=(
            r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"
            r"|https://[a-z0-9-]+\.ngrok(-free)?\.app"
            r"|https://[a-z0-9-]+\.ngrok\.io"
            r"|https://[a-z0-9-]+\.ngrok\.dev"
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception):
        import logging

        logging.getLogger(__name__).exception("Unhandled API error: %s", exc)
        from sqlalchemy.exc import OperationalError

        from app.utils.sqlite_retry import is_sqlite_locked_error

        if isinstance(exc, OperationalError) and is_sqlite_locked_error(exc):
            return JSONResponse(
                status_code=503,
                content={"detail": "Server is busy. Please try again in a few seconds."},
            )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    app.include_router(auth.router)
    app.include_router(leads.router)
    app.include_router(cv.router)
    app.include_router(brain.router)
    app.include_router(scraper.router)
    app.include_router(ai.router)
    app.include_router(campaigns.router)
    app.include_router(messages.router)
    app.include_router(dashboard.router)
    app.include_router(user_api_keys.router)
    app.include_router(settings_routes.router)
    app.include_router(payments.router)
    app.include_router(email_outreach.router)
    app.include_router(support.router)
    app.include_router(whatsapp_chat.router)
    app.include_router(whatsapp_web.router)
    app.include_router(whatsapp_webhook.router)
    app.include_router(admin.router)

    @app.get("/health", tags=["health"], summary="Health check")
    def health_check():
        settings = get_settings()
        warnings: list[str] = []
        if settings.SECRET_KEY == "change-me-in-production-use-a-long-random-string":
            warnings.append("default_secret_key")
        payload: dict = {
            "status": "healthy",
            "version": settings.APP_VERSION,
        }
        if warnings:
            payload["warnings"] = warnings
        return payload

    return app


app = create_app()
