"""Modelo do ``plan.json``: a fonte única da verdade de um comercial."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.services.commercial.components import ACTIONS, PROPS_MODELS, ComponentName, target_ids

PLAN_FILE = "plan.json"
StepStatus = Literal["pending", "done", "failed"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Word(_Model):
    text: str
    start: float
    end: float


# Caminhos dentro do projeto: nunca absolutos nem com "..".
AUDIO_PATH = r"^audio/[A-Za-z0-9_-]+\.mp3$"
MEDIA_PATH = r"^media/[A-Za-z0-9_-][A-Za-z0-9._-]*$"
MUSIC_PATH = r"^(music|resource/songs)/[^/\\.][^/\\]*$"


class SceneAudio(_Model):
    file: str = Field(pattern=AUDIO_PATH)
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
    media: str | None = Field(default=None, pattern=MEDIA_PATH)
    audio: SceneAudio | None = None

    @model_validator(mode="after")
    def _normalize_props(self) -> "Scene":
        # Guarda os props já convertidos para os tipos declarados (e com os
        # padrões preenchidos), para que o lado Remotion receba exatamente o
        # que foi validado aqui. Props inválidos ficam como estão e são
        # relatados por validate_plan.
        try:
            model = PROPS_MODELS[self.component].model_validate(self.props)
        except ValidationError:
            return self
        self.props = model.model_dump(mode="json")
        return self


class Brief(_Model):
    topic: str
    audience: str
    target_seconds: int = Field(default=45, ge=30, le=60)
    tone: str = ""
    cta: str = ""


class VoiceSettings(_Model):
    provider: Literal["edge"] = "edge"
    name: str = "pt-BR-AntonioNeural"
    rate: str = Field(default="+8%", pattern=r"^[+-]\d{1,3}%$")
    scene_gap_seconds: float = 0.25


class MusicSettings(_Model):
    file: str | None = Field(default=None, pattern=MUSIC_PATH)
    speech_db: float = Field(default=-18, ge=-60, le=0)
    gap_db: float = Field(default=-9, ge=-60, le=0)
    fade_in: float = Field(default=0.5, ge=0, le=10)
    fade_out: float = Field(default=1.5, ge=0, le=10)


class CaptionSettings(_Model):
    enabled: bool = True
    max_words: int = Field(default=4, ge=1, le=8)
    max_chars: int = Field(default=18, ge=6, le=40)
    y_percent: float = Field(default=68, ge=5, le=95)
    font_size: int = Field(default=64, ge=24, le=120)
    highlight_color: str = Field(default="#8FB8FF", pattern=r"^#[0-9A-Fa-f]{6}$")


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


def text_hash(text: str, voice: VoiceSettings) -> str:
    """Identifica o par (texto, voz) de uma narração gerada."""
    payload = f"{voice.provider}|{voice.name}|{voice.rate}|{text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


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


def _phrase_in_text(text: str, phrase: str) -> bool:
    # Import tardio: captions importa Word deste módulo.
    from app.services.commercial.captions import find_phrase, tokenize

    return find_phrase(tokenize(text), phrase) is not None


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
