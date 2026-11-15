"""Execução em segundo plano das etapas do comercial, com log para a WebUI."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

Step = Literal["plan", "narrate", "render"]
Work = Callable[[Callable[[str], None]], None]
MAX_LOG_LINES = 400


class JobBusyError(RuntimeError):
    """Já existe uma etapa em execução para este projeto."""


@dataclass
class JobState:
    step: str
    status: Literal["running", "done", "failed"] = "running"
    logs: list[str] = field(default_factory=list)
    error: str | None = None


_lock = threading.Lock()
_jobs: dict[str, JobState] = {}
_by_project: dict[str, str] = {}


def _key(project_dir: Path) -> str:
    return str(Path(project_dir).resolve())


def submit(project_dir: Path, step: Step, work: Work) -> str:
    """Inicia ``work(log)`` em uma thread. Um job por projeto de cada vez."""
    key = _key(project_dir)
    with _lock:
        running = _jobs.get(_by_project.get(key, ""))
        if running is not None and running.status == "running":
            raise JobBusyError(f"etapa '{running.step}' ainda em execução neste projeto")
        job_id = uuid.uuid4().hex
        state = JobState(step=step)
        _jobs[job_id] = state
        _by_project[key] = job_id

    def log(line: str) -> None:
        with _lock:
            state.logs.append(line)
            del state.logs[:-MAX_LOG_LINES]

    def run() -> None:
        try:
            work(log)
        except Exception as exc:  # noqa: BLE001 - o erro vai para a interface
            with _lock:
                state.error = str(exc) or type(exc).__name__
                state.status = "failed"
        else:
            with _lock:
                state.status = "done"

    threading.Thread(target=run, name=f"commercial-{step}", daemon=True).start()
    return job_id


def get(job_id: str) -> JobState | None:
    with _lock:
        state = _jobs.get(job_id)
        if state is None:
            return None
        return JobState(step=state.step, status=state.status, logs=list(state.logs), error=state.error)


def current(project_dir: Path) -> JobState | None:
    """Último job do projeto (em execução ou terminado), se houver."""
    with _lock:
        job_id = _by_project.get(_key(project_dir))
    return get(job_id) if job_id else None
