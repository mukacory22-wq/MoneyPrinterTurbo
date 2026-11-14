"""Renderização: Remotion (imagem + áudio) → FFmpeg (volume final) → verificação."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from app.services.commercial.captions import CaptionGroup, to_srt
from app.services.commercial.schema import Plan, Word, load_plan, save_plan
from app.services.commercial.sfx import SFX_NAMES, resolve_sfx
from app.services.commercial.timeline import build_render_props, resolve_music

REPO_ROOT = Path(__file__).resolve().parents[3]
REMOTION_DIR = REPO_ROOT / "remotion"

TARGET_LUFS = -14.0
LUFS_TOLERANCE = 1.0
MAX_TRUE_PEAK = -1.0
# Folga de 0,5 dB: a codificação AAC pode elevar um pouco o pico.
LOUDNORM_TP = -1.5
LOUDNORM_LRA = 11
MIN_SECONDS, MAX_SECONDS = 30.0, 60.0

Log = Callable[[str], None]


class RenderError(RuntimeError):
    """A renderização falhou; a mensagem traz a causa."""


def _link(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def stage_public_dir(project_dir: Path, plan: Plan) -> Path:
    """Monta ``out/public`` com tudo que o Remotion lê via ``staticFile``."""
    project_dir = Path(project_dir)
    public = project_dir / "out" / "public"
    if public.exists():
        shutil.rmtree(public)
    public.mkdir(parents=True)
    for folder in ("audio", "media"):
        source = project_dir / folder
        if source.is_dir():
            for item in sorted(source.iterdir()):
                if item.is_file():
                    _link(item, public / folder / item.name)
    for name in SFX_NAMES:
        _link(resolve_sfx(name), public / "sfx" / f"{name}.wav")
    music = resolve_music(plan, project_dir)
    if music is not None:
        _link(music, public / "music" / music.name)
    return public


def _run(cmd: list[str], cwd: Path | None, log: Log) -> tuple[int, list[str]]:
    process = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    lines: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        line = line.rstrip()
        if line:
            lines.append(line)
            log(line)
    return process.wait(), lines


def render_raw(project_dir: Path, props_path: Path, public_dir: Path, log: Log = print) -> Path:
    """Chama o Remotion e devolve ``out/raw.mp4`` (H.264 + AAC, sem normalizar)."""
    if not (REMOTION_DIR / "node_modules").is_dir():
        raise RenderError(
            "dependências do Remotion não instaladas: rode `npm --prefix remotion install`"
        )
    code, lines = _run(
        ["npm", "run", "--silent", "validate", "--", str(props_path.resolve())], REMOTION_DIR, log
    )
    if code != 0:
        raise RenderError("plano inválido para o Remotion:\n" + "\n".join(lines[-30:]))

    raw = Path(project_dir) / "out" / "raw.mp4"
    cmd = [
        "npx", "remotion", "render", "src/index.ts", "Commercial", str(raw.resolve()),
        f"--props={props_path.resolve()}",
        f"--public-dir={public_dir.resolve()}",
        "--codec=h264", "--audio-codec=aac", "--crf=18", "--pixel-format=yuv420p",
        f"--concurrency={os.cpu_count() or 2}",
    ]
    code, lines = _run(cmd, REMOTION_DIR, log)
    if code != 0 or not raw.is_file():
        raise RenderError("Remotion falhou:\n" + "\n".join(lines[-30:]))
    return raw


def _ffmpeg(args: list[str]) -> str:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-y", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderError(f"ffmpeg falhou: {result.stderr[-600:]}")
    return result.stderr


def finalize(raw: Path, final: Path) -> None:
    """Normaliza o volume (loudnorm em duas passadas) sem recodificar o vídeo."""
    base = f"loudnorm=I={TARGET_LUFS}:TP={LOUDNORM_TP}:LRA={LOUDNORM_LRA}"
    stderr = _ffmpeg(["-i", str(raw), "-vn", "-af", f"{base}:print_format=json", "-f", "null", "-"])
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr, re.S)
    if not match:
        raise RenderError("não foi possível medir o volume do vídeo")
    m = json.loads(match.group(0))
    second = (
        f"{base}:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
        f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
        f":offset={m['target_offset']}:linear=true"
    )
    final.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg([
        "-i", str(raw), "-c:v", "copy", "-af", second,
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(final),
    ])


def verify(final: Path) -> list[str]:
    """Confere o MP4 final. Lista vazia = dentro do padrão."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration", "-of", "json",
         str(final)],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        return [f"arquivo ilegível: {probe.stderr.strip()}"]
    info = json.loads(probe.stdout)
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    problems: list[str] = []
    if video is None:
        problems.append("sem faixa de vídeo")
    else:
        if (video["width"], video["height"]) != (1080, 1920):
            problems.append(f"resolução {video['width']}x{video['height']} (esperado 1080x1920)")
        num, den = (int(x) for x in video["r_frame_rate"].split("/"))
        if abs(num / den - 30) > 0.01:
            problems.append(f"taxa de quadros {num / den:.2f} (esperado 30)")
        if video["codec_name"] != "h264":
            problems.append(f"codec de vídeo {video['codec_name']} (esperado h264)")
    if audio is None:
        problems.append("sem faixa de áudio")
    elif audio["codec_name"] != "aac":
        problems.append(f"codec de áudio {audio['codec_name']} (esperado aac)")

    duration = float(info["format"]["duration"])
    if not MIN_SECONDS <= duration <= MAX_SECONDS:
        problems.append(
            f"duração {duration:.1f} s fora de {MIN_SECONDS:.0f}–{MAX_SECONDS:.0f} s"
        )

    if audio is not None:
        stderr = subprocess.run(
            ["ffmpeg", "-hide_banner", "-i", str(final), "-vn", "-af", "ebur128=peak=true",
             "-f", "null", "-"],
            capture_output=True, text=True,
        ).stderr
        summary = stderr[stderr.rfind("Summary:"):]
        loud = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
        peak = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary)
        if not loud or not peak:
            problems.append("não foi possível medir o volume")
        else:
            lufs, true_peak = float(loud.group(1)), float(peak.group(1))
            if abs(lufs - TARGET_LUFS) > LUFS_TOLERANCE:
                problems.append(f"volume {lufs:.1f} LUFS (esperado {TARGET_LUFS:.0f} ±1)")
            if true_peak > MAX_TRUE_PEAK + 0.05:
                problems.append(f"pico {true_peak:.1f} dBTP (máximo {MAX_TRUE_PEAK:.0f})")
    return problems


def _write_srt(props: dict, path: Path) -> None:
    fps = props["fps"]
    groups = [
        CaptionGroup(
            words=[Word(text=w["text"], start=w["frame"] / fps, end=w["frame"] / fps) for w in g["words"]],
            start=g["from"] / fps,
            end=g["to"] / fps,
        )
        for g in props["captions"]["groups"]
    ]
    path.write_text(to_srt(groups), encoding="utf-8")


def render_project(project_dir: Path, log: Log = print) -> Path:
    """Fluxo completo de render. Atualiza ``status.render`` no plano."""
    project_dir = Path(project_dir)
    plan = load_plan(project_dir)
    out = project_dir / "out"
    out.mkdir(parents=True, exist_ok=True)
    final = out / "final.mp4"
    try:
        try:
            props = build_render_props(plan, project_dir=project_dir)
        except ValueError as exc:
            raise RenderError(str(exc)) from exc
        props_path = out / "props.json"
        props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        public = stage_public_dir(project_dir, plan)
        log(f"Renderizando {props['durationInFrames'] / props['fps']:.1f} s ({len(props['scenes'])} cenas)…")
        raw = render_raw(project_dir, props_path, public, log)
        log("Normalizando o volume…")
        finalize(raw, final)
        problems = verify(final)
        if problems:
            raise RenderError("vídeo fora do padrão: " + "; ".join(problems))
        _write_srt(props, out / "final.srt")
    except RenderError as exc:
        plan.status.render = "failed"
        plan.status.errors["render"] = str(exc)
        save_plan(project_dir, plan)
        raise
    plan.status.render = "done"
    plan.status.errors.pop("render", None)
    save_plan(project_dir, plan)
    log(f"Pronto: {final}")
    return final
