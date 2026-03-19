from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.db.redis import close_redis, init_redis
from app.db.session import init_db
from app.middleware.gateway import GatewayMiddleware


# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"Starting {settings.app_name} v{settings.app_version} [{settings.app_env}]")

    await init_db()
    await init_redis()

    yield

    logger.info("Shutting down…")
    await close_redis()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API Gateway with distributed rate limiting, JWT authentication, "
            "API key management, and per-user/per-endpoint sliding-window rate limiting."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Used",
            "X-Response-Time-Ms",
        ],
    )

    # ------------------------------------------------------------------ #
    # Gateway middleware (API key validation + rate limiting + logging)
    # ------------------------------------------------------------------ #
    app.add_middleware(GatewayMiddleware)

    # ------------------------------------------------------------------ #
    # Routers
    # ------------------------------------------------------------------ #
    app.include_router(api_router)

    # ------------------------------------------------------------------ #
    # Exception handlers
    # ------------------------------------------------------------------ #
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error on {request.url}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception on {request.url}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # ------------------------------------------------------------------ #
    # Health check (no auth)
    # ------------------------------------------------------------------ #
    @app.get("/health", tags=["Health"], summary="Service health check")
    async def health():
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
            "env": settings.app_env,
        }

    return app


app = create_app()
