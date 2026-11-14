"""Modelo do ``plan.json``: a fonte única da verdade de um comercial."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.commercial.components import ACTIONS, PROPS_MODELS, ComponentName, target_ids

PLAN_FILE = "plan.json"
StepStatus = Literal["pending", "done", "failed"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Word(_Model):
    text: str
    start: float
    end: float


class SceneAudio(_Model):
    file: str
    duration: float
    words: list[Word]
    text_hash: str
    raw_words: list[Word] = []


class Action(_Model):
    at: str = Field(min_length=1)
    do: str
    target: str | None = None


class SceneSfx(_Model):
    enabled: bool = True


class Scene(_Model):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    narration: str = Field(min_length=1)
    emphasis: list[str] = []
    component: ComponentName
    props: dict = {}
    actions: list[Action] = []
    camera: Literal["push_in", "drift", "static"] = "push_in"
    transition: Literal["blur_zoom", "morph", "cut"] = "blur_zoom"
    sfx: SceneSfx = SceneSfx()
    media: str | None = None
    audio: SceneAudio | None = None


class Brief(_Model):
    topic: str
    audience: str
    target_seconds: int = Field(default=45, ge=30, le=60)
    tone: str = ""
    cta: str = ""


class VoiceSettings(_Model):
    provider: Literal["edge"] = "edge"
    name: str = "pt-BR-AntonioNeural"
    rate: str = "+8%"
    scene_gap_seconds: float = 0.25


class MusicSettings(_Model):
    file: str | None = None
    speech_db: float = -18
    gap_db: float = -9
    fade_in: float = 0.5
    fade_out: float = 1.5


class CaptionSettings(_Model):
    enabled: bool = True
    max_words: int = 4
    max_chars: int = 18
    y_percent: float = 60
    font_size: int = 64
    highlight_color: str = "#8FB8FF"


class Status(_Model):
    plan: StepStatus = "pending"
    narration: StepStatus = "pending"
    render: StepStatus = "pending"
    errors: dict[str, str] = {}


class Plan(_Model):
    version: Literal[1] = 1
    id: str = Field(pattern=r"^[a-z0-9-]{3,64}$")
    brief: Brief
    voice: VoiceSettings = VoiceSettings()
    music: MusicSettings = MusicSettings()
    captions: CaptionSettings = CaptionSettings()
    scenes: list[Scene] = Field(min_length=3, max_length=14)
    status: Status = Status()


def load_plan(project_dir: Path) -> Plan:
    path = Path(project_dir) / PLAN_FILE
    return Plan.model_validate_json(path.read_text(encoding="utf-8"))


def save_plan(project_dir: Path, plan: Plan) -> None:
    """Grava o plano de forma atômica (arquivo temporário + ``os.replace``)."""
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=project_dir, prefix=".plan-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        os.replace(tmp, project_dir / PLAN_FILE)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _normalize(text: str) -> list[str]:
    import re
    import unicodedata

    flat = unicodedata.normalize("NFKD", text.lower())
    flat = "".join(ch for ch in flat if not unicodedata.combining(ch))
    tokens = [re.sub(r"[^a-z0-9]", "", tok) for tok in flat.split()]
    return [tok for tok in tokens if tok]


def _phrase_in_text(text: str, phrase: str) -> bool:
    words, target = _normalize(text), _normalize(phrase)
    if not target:
        return False
    return any(words[i : i + len(target)] == target for i in range(len(words) - len(target) + 1))


def validate_plan(plan: Plan) -> list[str]:
    """Regras semânticas que o pydantic não cobre. Lista vazia = plano ok."""
    errors: list[str] = []
    seen: set[str] = set()
    for scene in plan.scenes:
        prefix = f"cena {scene.id}"
        if scene.id in seen:
            errors.append(f"{prefix}: id duplicado")
        seen.add(scene.id)

        try:
            PROPS_MODELS[scene.component].model_validate(scene.props)
        except ValidationError as exc:
            details = "; ".join(
                f"{'.'.join(str(p) for p in e['loc']) or '(raiz)'}: {e['msg']}"
                for e in exc.errors()
            )
            errors.append(f"{prefix}: props inválidos para {scene.component} ({details})")

        ids = target_ids(scene.component, scene.props)
        allowed = ACTIONS[scene.component]
        for action in scene.actions:
            if action.do not in allowed:
                errors.append(
                    f"{prefix}: ação '{action.do}' não existe em {scene.component} "
                    f"(permitidas: {', '.join(sorted(allowed)) or 'nenhuma'})"
                )
            if action.target is not None and action.target not in ids:
                errors.append(f"{prefix}: alvo '{action.target}' não existe nos props")
            if not _phrase_in_text(scene.narration, action.at):
                errors.append(f"{prefix}: trecho da ação '{action.at}' não está na narração")

        for word in scene.emphasis:
            if not _phrase_in_text(scene.narration, word):
                errors.append(f"{prefix}: destaque '{word}' não está na narração")

        if scene.component == "Media" and not scene.media:
            errors.append(f"{prefix}: componente Media exige o campo media")
    return errors
