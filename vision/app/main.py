"""Freda Verify Vision AI service (internal). Reads identity documents with a self-hosted vision-language model. It is NOT public: it listens on the internal network only and every call
needs the shared token. It describes and extracts; it never decides (see schema.py)."""
import asyncio
import hmac
import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    Request,
    UploadFile,
)
from fastapi.responses import JSONResponse

from . import imaging
from .config import Settings, get_settings
from .engine import Engine, FakeEngine, ModelError, ModelUnavailable, OpenAICompatEngine
from .schema import AnalyzeResult, DocType, Status

log = logging.getLogger("vision")          # logs carry ids, sizes, timings and status codes: NEVER document content or extracted text


class Api(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def build_engine(s: Settings) -> Engine:
    if s.engine == "fake":
        if s.env == "prod":
            raise RuntimeError("the fake engine is not allowed in prod")
        return FakeEngine()
    return OpenAICompatEngine(s.llm_url, s.llm_model, s.timeout_s)


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    s = settings or get_settings()
    if s.env == "prod" and len(s.token) < 32:
        raise RuntimeError("FV_VISION_TOKEN (>= 32 characters) is required in prod")
    app = FastAPI(title="Freda Verify Vision AI", docs_url=None if s.env == "prod" else "/docs", redoc_url=None)
    app.state.engine = engine or build_engine(s)
    app.state.sem = asyncio.Semaphore(s.max_concurrent)
    app.state.waiting = 0
    hits: dict[str, deque] = defaultdict(deque)

    @app.exception_handler(Api)
    async def _api(_: Request, e: Api):
        return JSONResponse({"error": {"code": e.code, "message": e.message}}, status_code=e.status)

    def auth(authorization: str | None = Header(default=None)) -> str:
        if not s.token or not authorization or not authorization.startswith("Bearer ") or not hmac.compare_digest(authorization[7:], s.token):
            raise Api(401, "unauthorized", "Missing or invalid service token")
        now = time.monotonic()
        q = hits["svc"]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= s.rate_per_minute:
            raise Api(429, "rate_limited", "Too many requests")
        q.append(now)
        return "svc"

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready():
        ok = await app.state.engine.ready()
        return JSONResponse({"status": "ready" if ok else "model_unavailable", "engine": app.state.engine.name, "model": app.state.engine.model}, status_code=200 if ok else 503)

    @app.post("/api/v1/vision/analyze", response_model=AnalyzeResult)
    async def analyze(request: Request, image: UploadFile = File(...), document_type: DocType = Form(...), instructions: str | None = Form(default=None, max_length=300),  # noqa: B008
                      _: str = Depends(auth)):
        rid = "vis_" + uuid.uuid4().hex[:16]
        t0 = time.monotonic()
        if int(request.headers.get("content-length") or 0) > s.max_upload_bytes + 64 * 1024:
            raise Api(413, "too_large", "Image is too large")
        data = await image.read(s.max_upload_bytes + 1)
        if len(data) > s.max_upload_bytes:
            raise Api(413, "too_large", "Image is too large")
        try:
            img = imaging.load(data, s.max_pixels)
        except imaging.ImageError as e:
            raise Api(422, e.code, str(e)) from e
        q = imaging.quality(img)
        jpeg = imaging.prepare(img, s.max_side)
        if app.state.waiting >= s.max_queued:
            raise Api(429, "busy", "The reading queue is full, try again shortly")
        app.state.waiting += 1
        acquired = False
        try:
            async with app.state.sem:
                app.state.waiting -= 1
                acquired = True
                try:
                    ans = await asyncio.wait_for(app.state.engine.analyze(jpeg, document_type.value, instructions), timeout=s.timeout_s)
                except TimeoutError as e:
                    raise Api(504, "timeout", "The model took too long") from e
                except ModelUnavailable as e:
                    raise Api(503, "model_unavailable", "The vision model is not available") from e
                except ModelError as e:
                    raise Api(502, "model_error", "The model did not return a usable answer") from e
        finally:
            if not acquired:                                                   # cancelled / failed while still queued
                app.state.waiting -= 1
        status = Status.ok
        if ans.missing_information or not q.usable:
            status = Status.partial
        if not ans.fields and not ans.extracted_text.strip():
            status = Status.failed
        log.info("analyze %s doc=%s bytes=%d status=%s ms=%d", rid, document_type.value, len(data), status.value, (time.monotonic() - t0) * 1000)
        return AnalyzeResult(request_id=rid, status=status, requested_document_type=document_type, document_type=ans.document_type, extracted_text=ans.extracted_text,
                             fields=ans.fields, image_quality=q, missing_information=ans.missing_information, suspicious_visual_anomalies=ans.suspicious_visual_anomalies,
                             confidence=ans.overall_confidence, model=app.state.engine.model, engine=app.state.engine.name)

    return app


app = create_app() if __name__ != "__main__" and get_settings().token else None
