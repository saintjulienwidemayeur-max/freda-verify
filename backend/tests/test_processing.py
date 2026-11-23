from datetime import timedelta

from sqlalchemy import select

from app.api.v1 import verifications as V
from app.db.session import SessionLocal
from app.models import Verification
from tests.test_media import auth, bearer, setup, submit_all


def _row(vid):
    with SessionLocal() as db:
        return db.get(Verification, vid)


def test_submission_ends_in_manual_review_when_nobody_decided_automatically(client):
    t, org, key, v = setup(client)                                   # manual mode
    assert submit_all(client, v["session_token"]).status_code == 204
    # the test client runs the background pipeline before returning: it must have settled PROCESSING -> MANUAL_REVIEW
    assert _row(v["id"]).status == "MANUAL_REVIEW"


def test_complete_sets_processing_before_the_pipeline_runs(client, monkeypatch):
    t, org, key, v = setup(client)
    monkeypatch.setattr(V, "run_pipeline", lambda vid: None)         # pipeline never runs (e.g. the server restarted)
    assert submit_all(client, v["session_token"]).status_code == 204
    assert _row(v["id"]).status == "PROCESSING"
    got = client.get(f"/api/v1/verifications/{v['id']}", headers=bearer(key)).json()
    assert got["status"] == "PROCESSING"


def test_a_stuck_processing_case_becomes_reviewable_after_the_delay(client, monkeypatch):
    t, org, key, v = setup(client)
    monkeypatch.setattr(V, "run_pipeline", lambda vid: None)
    submit_all(client, v["session_token"])
    d = f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/decision"
    assert client.post(d, json={"decision": "APPROVED"}, headers=auth(t)).status_code == 409      # still in progress: not yet reviewable
    with SessionLocal() as db:
        row = db.scalar(select(Verification).where(Verification.id == v["id"]))
        row.submitted_at = row.submitted_at - timedelta(minutes=31)
        db.commit()
    assert client.get(f"/api/v1/verifications/{v['id']}", headers=bearer(key)).json()["status"] == "MANUAL_REVIEW"
    assert client.post(d, json={"decision": "APPROVED"}, headers=auth(t)).status_code == 200


def test_jobs_run_in_order_on_one_worker_and_survive_a_failing_job(monkeypatch):
    import threading
    import time

    from app.core.config import get_settings
    from app.services import jobs
    monkeypatch.setattr(get_settings(), "app_env", "dev")           # the real queue (tests normally run jobs inline)
    seen, names = [], set()
    done = threading.Event()

    def boom():
        raise RuntimeError("bad job")

    def job(n):
        names.add(threading.current_thread().name)
        seen.append(n)
        if n == 3:
            done.set()

    jobs.submit(boom)
    for n in (1, 2, 3):
        jobs.submit(job, n)
    assert done.wait(5)
    time.sleep(0.05)
    assert seen == [1, 2, 3] and names == {"verification-worker"}
