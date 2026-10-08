from fastapi import FastAPI
from app.api.shadow import router as shadow_router
from fastapi import Request
from fastapi.responses import JSONResponse
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)

import time
import uuid
import json
from starlette.middleware.base import BaseHTTPMiddleware

class SafeLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Redact sensitive headers
        safe_headers = dict(request.headers)
        if "authorization" in safe_headers:
            safe_headers["authorization"] = "[REDACTED]"
            
        logger.info(json.dumps({
            "event": "request_started",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        }))
        
        try:
            response = await call_next(request)
            duration = round((time.time() - start_time) * 1000, 2)
            
            logger.info(json.dumps({
                "event": "request_finished",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration
            }))
            return response
        except Exception as e:
            duration = round((time.time() - start_time) * 1000, 2)
            logger.error(json.dumps({
                "event": "request_failed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error_type": type(e).__name__,
                "duration_ms": duration
            }))
            raise

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

def validate_safety_config():
    if settings.ENABLE_LIVE_TRADING:
        raise RuntimeError("LIVE_EXECUTION_BLOCKED: ENABLE_LIVE_TRADING must be false")
    if settings.LIVE_EXECUTION_UNLOCKED:
        raise RuntimeError("LIVE_EXECUTION_BLOCKED: LIVE_EXECUTION_UNLOCKED must be false")
    if not settings.BROKER_EXECUTION_BLOCKED:
        raise RuntimeError("LIVE_EXECUTION_BLOCKED: BROKER_EXECUTION_BLOCKED must be true")
    if settings.EXECUTION_MODE == "LIVE":
        raise RuntimeError("LIVE_EXECUTION_BLOCKED: EXECUTION_MODE cannot be LIVE without unlock")

validate_safety_config()

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SafeLoggingMiddleware)

if settings.FRONTEND_ORIGIN:
    origins = [origin.strip() for origin in settings.FRONTEND_ORIGIN.split(",")]
    if "http://localhost:5173" not in origins:
        origins.append("http://localhost:5173")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )

@app.get("/health")
def root_health_check():
    return {"status": "healthy"}

app.include_router(api_router, prefix="/api/v1")
app.include_router(shadow_router, prefix="/api/v1")

