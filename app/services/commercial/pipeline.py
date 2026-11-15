"""Gerência de projetos de comercial: pastas, listagem e invalidação de etapas."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from app.services.commercial.narration import text_hash
from app.services.commercial.schema import PLAN_FILE, Plan

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECTS_ROOT = REPO_ROOT / "storage" / "commercials"
MAX_ID_LENGTH = 48


def _slug(text: str) -> str:
    flat = unicodedata.normalize("NFKD", text.lower())
    flat = "".join(ch for ch in flat if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-z0-9]+", "-", flat).strip("-")[:MAX_ID_LENGTH].strip("-")
    return slug if len(slug) >= 3 else "comercial"


def new_project_dir(topic: str, root: Path = PROJECTS_ROOT) -> Path:
    """Pasta (ainda não criada) para um novo projeto; o nome é o id do plano."""
    base = _slug(topic)
    candidate, counter = base, 1
    while (Path(root) / candidate).exists():
        counter += 1
        suffix = f"-{counter}"
        candidate = base[: MAX_ID_LENGTH - len(suffix)].rstrip("-") + suffix
    return Path(root) / candidate


def list_projects(root: Path = PROJECTS_ROOT) -> list[Path]:
    """Projetos com plano, do mais recente para o mais antigo."""
    root = Path(root)
    if not root.is_dir():
        return []
    found = [p for p in root.iterdir() if (p / PLAN_FILE).is_file()]
    return sorted(found, key=lambda p: (p / PLAN_FILE).stat().st_mtime, reverse=True)


def invalidate_stale(plan: Plan) -> list[str]:
    """Descarta o áudio das cenas cujo texto ou voz mudou. Devolve os ids afetados."""
    changed: list[str] = []
    for scene in plan.scenes:
        if scene.audio and scene.audio.text_hash != text_hash(scene.narration, plan.voice):
            scene.audio = None
            changed.append(scene.id)
    if changed or any(scene.audio is None for scene in plan.scenes):
        plan.status.narration = "pending"
        plan.status.render = "pending"
    return changed
