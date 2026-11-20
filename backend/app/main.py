import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import auth, orgs, tools
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.middleware import RequestContext
from app.db.session import get_engine


def create_app() -> FastAPI:
    s = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    app = FastAPI(title="Freda Verify API", version="0.1.0", docs_url="/docs" if s.app_env != "prod" else None, redoc_url=None,
                  openapi_url="/openapi.json" if s.app_env != "prod" else None)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=False, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                       allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"], expose_headers=["X-Request-ID", "Retry-After"])
    app.add_middleware(RequestContext)
    install_error_handlers(app)

    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(auth.router)
    v1.include_router(orgs.router)
    v1.include_router(tools.router)
    app.include_router(v1)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    def ready():
        with get_engine().connect() as c:
            c.execute(text("select 1"))
        return {"status": "ready"}

    return app


app = create_app()
