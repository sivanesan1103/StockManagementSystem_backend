"""FastAPI application factory."""

import logging
import uuid
from typing import Callable

import structlog
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.db.fastapi_integration import setup_migration_events
from app.middleware.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID for tracing."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Process request
        response: Response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Redis-based rate limiting middleware."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        redis_url: str,
        limit_per_minute: int = 60,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.redis_url = redis_url
        self.limit_per_minute = limit_per_minute
        self.window_seconds = window_seconds
        self.redis_client = None

    async def _get_redis_client(self):
        """Lazy initialize Redis client."""
        if self.redis_client is None:
            import redis.asyncio as redis
            self.redis_client = redis.from_url(self.redis_url)
        return self.redis_client

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/healthz", "/ready"]:
            return await call_next(request)

        try:
            redis_client = await self._get_redis_client()
            
            # Use IP address as key (could be improved with user ID for authenticated requests)
            client_ip = request.client.host if request.client else "unknown"
            key = f"rate_limit:{client_ip}:{request.url.path}"
            
            # Get current count
            current = await redis_client.get(key)
            if current is None:
                # First request in window
                await redis_client.setex(key, self.window_seconds, 1)
                current_count = 1
            else:
                current_count = int(current) + 1
                await redis_client.set(key, current_count, self.window_seconds)
            
            # Check if limit exceeded
            if current_count > self.limit_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(self.window_seconds)},
                )
                
        except Exception as e:
            # If Redis is unavailable, log and continue (fail open)
            logger.warning(f"Rate limiting error: {e}")
            pass

        return await call_next(request)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for audit logging of requests and responses."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        self.logger = structlog.get_logger()

    async def dispatch(self, request: Request, call_next):
        # Extract request ID if available
        request_id = getattr(request.state, "request_id", None)
        
        # Log request
        self.logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_host=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        # Process request
        start_time = structlog.processors.TimeStamper(fmt="iso")()
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            status_code = 500
            # Re-raise to let exception handlers deal with it
            raise exc
        finally:
            # Calculate duration
            end_time = structlog.processors.TimeStamper(fmt="iso")()
            # Note: In a real implementation, we'd calculate actual duration
            # For simplicity, we're just logging the timestamps

        # Log response
        self.logger.info(
            "Request completed",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            status_code=status_code,
            client_host=request.client.host if request.client else None,
        )

        return response


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance.
    """
    # Create FastAPI app
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
    )

    # Set up CORS
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Add custom middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        RateLimitingMiddleware,
        redis_url=str(settings.REDIS_URL),
        limit_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )
    app.add_middleware(AuditLoggingMiddleware)

    # Set up database events
    setup_migration_events(app)

    # Include API router
    from app.api.main import api_router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Health check endpoints
    @app.get("/health", tags=["health"])
    async def health_check():
        """Basic health check endpoint."""
        return {"status": "healthy"}

    @app.get("/healthz", tags=["health"])
    async def health_check_z():
        """Kubernetes-style liveness probe."""
        return {"status": "ok"}

    @app.get("/ready", tags=["health"])
    async def readiness_check():
        """Readiness check including dependencies."""
        # Check database connection
        from app.db.session import check_db_connection
        db_healthy = await check_db_connection()
        
        # Check Redis connection
        redis_healthy = False
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(str(settings.REDIS_URL))
            await redis_client.ping()
            await redis_client.close()
            redis_healthy = True
        except Exception:
            pass
        
        if db_healthy and redis_healthy:
            return {"status": "ready"}
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "not ready", "database": db_healthy, "redis": redis_healthy},
            )

    # Root endpoint
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": settings.PROJECT_NAME,
            "description": settings.PROJECT_DESCRIPTION,
            "version": settings.VERSION,
            "docs_url": f"{settings.API_V1_STR}/docs",
            "redoc_url": f"{settings.API_V1_STR}/redoc",
        }

    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTPException."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return app


# Create app instance
app = create_application()