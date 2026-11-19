from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, goals, health, events
from app.api.routes import google_oauth, workflows
from app.production.settings import get_settings
from app.production.logging import configure_logging
from app.production.middleware import RequestControls
from app.runtime.multi_user_runtime import MultiUserRuntime


def create_app(runtime=None, settings=None):
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app):
        if runtime is None:
            google_values = {
                "client_id": getattr(settings, "google_client_id", ""),
                "client_secret": getattr(settings, "google_client_secret", ""),
                "redirect_uri": getattr(settings, "google_redirect_uri", ""),
            }
            configured = [bool(value) for value in google_values.values()]
            if any(configured) and not all(configured):
                raise ValueError("Set all three GOOGLE_* OAuth settings together.")
            google_config = google_values if all(configured) else None
            encryption_key = getattr(settings, "credential_encryption_key", "")
            if google_config and not encryption_key:
                raise ValueError("PAAI_CREDENTIAL_ENCRYPTION_KEY is required when Google OAuth is enabled.")
            app.state.paai_runtime = MultiUserRuntime(
                auth_database=settings.auth_database,
                token_secret=settings.auth_secret,
                token_lifetime_seconds=settings.token_lifetime_seconds,
                memory_database=settings.memory_database,
                autonomy_database=settings.autonomy_database,
                google_oauth_config=google_config,
                credential_database=getattr(settings, "credential_database", None) if google_config else None,
                credential_encryption_key=encryption_key if google_config else None,
            )
        else:
            app.state.paai_runtime = runtime
        yield
        repository = getattr(app.state.paai_runtime, "auth_repository", None)
        if repository is not None and hasattr(repository, "close"):
            repository.close()

    app = FastAPI(
        title="PAAI API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.add_middleware(
        RequestControls,
        max_body_bytes=settings.max_request_bytes,
        requests_per_minute=settings.requests_per_minute,
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(goals.router)
    app.include_router(events.router)
    app.include_router(workflows.router)
    app.include_router(google_oauth.router)
    app.add_api_route(
        "/auth/google/callback",
        google_oauth.google_callback,
        methods=["GET"],
        include_in_schema=False,
    )
    return app


app = create_app()
