from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, goals, health
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
            app.state.paai_runtime = MultiUserRuntime(
                auth_database=settings.auth_database,
                token_secret=settings.auth_secret,
                token_lifetime_seconds=settings.token_lifetime_seconds,
                memory_database=settings.memory_database,
                autonomy_database=settings.autonomy_database,
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
    )
    app.add_middleware(RequestControls, max_body_bytes=settings.max_request_bytes, requests_per_minute=settings.requests_per_minute)
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
    return app

app = create_app()
