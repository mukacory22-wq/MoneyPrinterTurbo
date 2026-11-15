import threading
import time

import pytest

from app.services.commercial import jobs


def _wait(job_id, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = jobs.get(job_id)
        if state.status != "running":
            return state
        time.sleep(0.02)
    raise AssertionError("job não terminou")


def test_job_runs_and_records_logs(tmp_path):
    def work(log):
        log("primeira linha")
        log("segunda linha")

    state = _wait(jobs.submit(tmp_path, "render", work))
    assert state.status == "done"
    assert state.logs == ["primeira linha", "segunda linha"]
    assert state.error is None


def test_job_failure_keeps_error(tmp_path):
    def work(log):
        raise RuntimeError("Remotion falhou: exemplo")

    state = _wait(jobs.submit(tmp_path, "render", work))
    assert state.status == "failed"
    assert "Remotion falhou: exemplo" in state.error


def test_job_busy_per_project(tmp_path):
    gate = threading.Event()
    first = jobs.submit(tmp_path, "narrate", lambda log: gate.wait(5))
    with pytest.raises(jobs.JobBusyError):
        jobs.submit(tmp_path, "render", lambda log: None)
    other = jobs.submit(tmp_path / "outro", "render", lambda log: None)
    gate.set()
    assert _wait(first).status == "done"
    assert _wait(other).status == "done"
    assert _wait(jobs.submit(tmp_path, "render", lambda log: None)).status == "done"


def test_current_job_for_project(tmp_path):
    assert jobs.current(tmp_path) is None
    job_id = jobs.submit(tmp_path, "plan", lambda log: log("ok"))
    _wait(job_id)
    state = jobs.current(tmp_path)
    assert state is not None and state.step == "plan" and state.logs == ["ok"]


def test_unknown_job():
    assert jobs.get("nao-existe") is None
