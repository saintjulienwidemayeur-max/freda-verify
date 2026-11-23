"""One background worker for the heavy verification work (OCR, face, liveness, decision).

Why: on a small instance (Render free: 0.15 CPU, 512 MB) running several verifications at the same time starves the whole API (logins, uploads) and can run out of memory
(each OCR reading starts Tesseract; the models take ~200-400 MB). Instead of one thread per submission, every submission is put in a FIFO queue and ONE worker thread processes them
one after another: the API stays responsive, memory is bounded by a single verification, and 50 people submitting together simply wait their turn (status PROCESSING).

Limits (honest): the queue lives in this process, so a restart loses it; at startup every case still in PROCESSING is queued again (`requeue_processing`). One worker means the
throughput is that of ONE verification at a time: ~1-2 minutes each on 0.15 CPU, a few seconds to ~20 s on a full core. In tests (`FV_APP_ENV=test`) jobs run immediately in the caller.
"""
from __future__ import annotations

import logging
import queue
import threading
import uuid
from collections.abc import Callable

from app.core.config import get_settings

log = logging.getLogger("freda.jobs")
_q: queue.Queue[tuple[Callable[..., None], tuple]] = queue.Queue()
_worker: threading.Thread | None = None
_start_lock = threading.Lock()


def _loop() -> None:
    while True:
        fn, args = _q.get()
        try:
            fn(*args)
        except Exception:  # noqa: BLE001  one bad job must never stop the worker
            log.exception("job failed")
        finally:
            _q.task_done()


def submit(fn: Callable[..., None], *args) -> None:
    if get_settings().app_env == "test":
        fn(*args)
        return
    global _worker
    with _start_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_loop, name="verification-worker", daemon=True)
            _worker.start()
    _q.put((fn, args))


def depth() -> int:
    return _q.qsize()


def requeue_processing() -> int:
    """At startup: queue again the verifications that were being processed when the previous process stopped. Returns how many."""
    from sqlalchemy import select

    from app.api.v1.verifications import run_pipeline
    from app.db.session import SessionLocal
    from app.models import Verification
    try:
        with SessionLocal() as db:
            ids: list[uuid.UUID] = list(db.scalars(select(Verification.id).where(Verification.status == "PROCESSING").order_by(Verification.submitted_at)))
        for i in ids:
            submit(run_pipeline, i)
        return len(ids)
    except Exception:  # noqa: BLE001
        log.warning("could not requeue PROCESSING verifications")
        return 0
