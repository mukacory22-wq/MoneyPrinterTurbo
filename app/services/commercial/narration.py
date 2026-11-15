"""Narração por cena com Edge TTS e tempos reais de cada palavra."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import aiohttp
import edge_tts
from edge_tts.exceptions import EdgeTTSException

from app.services.commercial.captions import AlignmentError, align_words
from app.services.commercial.ffmpeg_utils import probe_duration
from app.services.commercial.schema import (
    Plan, SceneAudio, VoiceSettings, Word, load_plan, save_plan, text_hash,
)
from app.services.commercial.timeline import TAIL_SECONDS

RETRY_DELAYS: tuple[float, ...] = (2, 6, 15)  # esperas entre as 4 tentativas
_NETWORK_ERRORS = (aiohttp.ClientError, EdgeTTSException, asyncio.TimeoutError, OSError)


class NarrationError(RuntimeError):
    """A narração de uma cena não pôde ser gerada."""


async def _stream_once(text: str, voice: VoiceSettings, out_path: Path) -> list[Word]:
    communicate = edge_tts.Communicate(
        text,
        voice.name,
        rate=voice.rate,
        boundary="WordBoundary",
        proxy=os.environ.get("HTTPS_PROXY") or None,
    )
    words: list[Word] = []
    with open(out_path, "wb") as fh:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append(
                    Word(text=chunk["text"], start=round(start, 3),
                         end=round(start + chunk["duration"] / 1e7, 3))
                )
    return words


async def synthesize_scene(
    text: str, voice: VoiceSettings, out_path: Path
) -> tuple[float, list[Word]]:
    """Gera o MP3 de uma cena. Devolve (duração, palavras cruas do TTS)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    attempts = len(RETRY_DELAYS) + 1
    for attempt in range(attempts):
        try:
            words = await _stream_once(text, voice, out_path)
            break
        except _NETWORK_ERRORS as exc:
            out_path.unlink(missing_ok=True)
            if attempt == attempts - 1:
                raise NarrationError(
                    f"Edge TTS falhou após {attempts} tentativas: {exc or type(exc).__name__}"
                ) from exc
            await asyncio.sleep(RETRY_DELAYS[attempt])
    if not out_path.exists() or out_path.stat().st_size == 0:
        out_path.unlink(missing_ok=True)
        raise NarrationError("Edge TTS não devolveu áudio")
    return probe_duration(out_path), words


def total_duration(plan: Plan) -> float:
    """Duração do vídeo final: falas + pausas entre cenas + respiro do fim."""
    narrated = [s for s in plan.scenes if s.audio]
    if not narrated:
        return 0.0
    return sum(s.audio.duration + plan.voice.scene_gap_seconds for s in narrated) + TAIL_SECONDS


def narrate_project(project_dir: Path, force: bool = False) -> Plan:
    """Gera a narração das cenas pendentes e grava o plano após cada cena."""
    project_dir = Path(project_dir)
    plan = load_plan(project_dir)
    plan.status.errors.pop("narration", None)
    for scene in plan.scenes:
        digest = text_hash(scene.narration, plan.voice)
        rel = f"audio/{scene.id}.mp3"
        current = scene.audio
        if (
            not force and current and current.text_hash == digest
            and (project_dir / current.file).exists()
        ):
            continue
        try:
            duration, raw = asyncio.run(
                synthesize_scene(scene.narration, plan.voice, project_dir / rel)
            )
            words = align_words(scene.narration, raw)
        except (NarrationError, AlignmentError, ValueError) as exc:
            plan.status.narration = "failed"
            plan.status.errors["narration"] = f"cena {scene.id}: {exc}"
            save_plan(project_dir, plan)
            raise NarrationError(plan.status.errors["narration"]) from exc
        scene.audio = SceneAudio(
            file=rel, duration=round(duration, 3), words=words, text_hash=digest, raw_words=raw
        )
        plan.status.narration = "pending"
        plan.status.render = "pending"
        save_plan(project_dir, plan)
    plan.status.narration = "done"
    save_plan(project_dir, plan)
    return plan
