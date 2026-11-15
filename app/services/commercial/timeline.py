"""Linha do tempo do comercial: transforma o plano em ``RenderProps``.

Toda a matemática de tempo vive aqui (quadros das cenas, palavras, ações,
legendas, envelope da trilha e efeitos sonoros). O Remotion apenas desenha o
resultado; o contrato está espelhado em ``remotion/src/types.ts``.
"""

from __future__ import annotations

from pathlib import Path

from app.services.commercial.captions import find_phrase, group_captions, tokenize, normalize_token
from app.services.commercial.ffmpeg_utils import probe_duration
from app.services.commercial.schema import Plan, Scene, text_hash

REPO_ROOT = Path(__file__).resolve().parents[3]
WIDTH, HEIGHT = 1080, 1920
TAIL_SECONDS = 0.8          # respiro após a última fala
RAMP_SECONDS = 0.2          # rampa do ducking
SPEECH_PAD_SECONDS = 0.1
SPEECH_MERGE_SECONDS = 0.4  # pausas menores que isto não levantam a trilha
WHOOSH_LEAD_FRAMES = 6
SFX_DB = -12
CAPTION_HOLD_FRAMES = 12

_ACTION_SFX = {
    "typing": "type", "type": "type", "write": "type",
    "press": "click", "check": "click", "choose": "click", "toggle": "click",
    "activate": "click", "mark": "click",
    "stamp": "impact", "count": "impact", "set": "impact",
    "scan": "shimmer", "route": "shimmer", "grow": "shimmer", "highlight": "shimmer",
    "send": "pop", "comment": "pop", "reveal": "pop", "done": "pop",
}


def _frames(seconds: float, fps: int) -> int:
    return int(seconds * fps + 0.5)


def action_sfx(component: str, do: str) -> str | None:
    if do == "show":
        return "notify" if component == "PhoneLockScreen" else "pop"
    return _ACTION_SFX.get(do)


def resolve_music(plan: Plan, project_dir: Path | None = None) -> Path | None:
    """Caminho da trilha: ``music/…`` (do projeto) ou ``resource/songs/…`` (do repositório)."""
    if not plan.music.file:
        return None
    folder, _, name = plan.music.file.rpartition("/")
    if folder == "music":
        base = Path(project_dir) / "music" if project_dir else None
    else:
        base = REPO_ROOT / "resource" / "songs"
    if base is not None:
        candidate = base / name
        # O schema já barra "..", mas confirma que o arquivo fica dentro da pasta.
        if candidate.is_file() and candidate.resolve().parent == base.resolve():
            return candidate
    raise ValueError(f"arquivo de trilha não encontrado: {plan.music.file}")


def envelope_db_at(envelope: list[dict], frame: float) -> float:
    """Interpolação linear (em dB) do envelope; igual à do lado Remotion."""
    if frame <= envelope[0]["frame"]:
        return envelope[0]["db"]
    for left, right in zip(envelope, envelope[1:]):
        if frame <= right["frame"]:
            span = right["frame"] - left["frame"]
            ratio = (frame - left["frame"]) / span if span else 1.0
            return left["db"] + (right["db"] - left["db"]) * ratio
    return envelope[-1]["db"]


def _speech_intervals(plan: Plan, starts: list[int], fps: int) -> list[tuple[int, int]]:
    spans: list[list[float]] = []
    for scene, start in zip(plan.scenes, starts):
        for word in scene.audio.words:
            begin = start / fps + word.start - SPEECH_PAD_SECONDS
            end = start / fps + word.end + SPEECH_PAD_SECONDS
            if spans and begin - spans[-1][1] < SPEECH_MERGE_SECONDS:
                spans[-1][1] = max(spans[-1][1], end)
            else:
                spans.append([begin, end])
    return [(max(_frames(b, fps), 0), _frames(e, fps)) for b, e in spans]


def _envelope(plan: Plan, starts: list[int], total: int, fps: int) -> list[dict]:
    speech, gap = plan.music.speech_db, plan.music.gap_db
    ramp = _frames(RAMP_SECONDS, fps)
    points: list[tuple[int, float]] = []

    def add(frame: int, db: float) -> None:
        frame = min(max(frame, 0), total)
        if points and frame <= points[-1][0]:
            if frame == points[-1][0]:
                points[-1] = (frame, db)
            return
        points.append((frame, db))

    intervals = _speech_intervals(plan, starts, fps)
    add(0, speech if intervals and intervals[0][0] <= 0 else gap)
    for begin, end in intervals:
        add(begin - ramp, gap)
        add(begin, speech)
        add(end, speech)
        add(end + ramp, gap)
    if points[-1][0] < total:
        add(total, points[-1][1])
    return [{"frame": f, "db": db} for f, db in points]


def _scene_actions(scene: Scene, fps: int) -> list[dict]:
    tokens = [t for t in tokenize(scene.narration) if normalize_token(t)]
    resolved = []
    for action in scene.actions:
        found = find_phrase(tokens, action.at)
        if found is None:
            raise ValueError(f"cena {scene.id}: trecho '{action.at}' não está na narração")
        word = scene.audio.words[found[0]]
        resolved.append({"do": action.do, "target": action.target, "frame": _frames(word.start, fps)})
    return resolved


def _scene_captions(plan: Plan, scene: Scene, start: int, end: int, fps: int) -> list[dict]:
    tokens = [t for t in tokenize(scene.narration) if normalize_token(t)]
    words = scene.audio.words
    emphasized: set[int] = set()
    phrases: list[tuple[int, int]] = []
    for phrase in scene.emphasis:
        found = find_phrase(tokens, phrase)
        if found:
            phrases.append(found)
            emphasized.update(range(found[0], found[1] + 1))

    settings = plan.captions
    groups = group_captions(
        words, tokens, settings.max_words, settings.max_chars, keep_together=phrases
    )
    out: list[dict] = []
    index = 0
    for group in groups:
        entries = []
        for word in group.words:
            entries.append({
                "text": word.text,
                "frame": start + _frames(word.start, fps),
                "emphasis": index in emphasized,
            })
            index += 1
        out.append({
            "from": entries[0]["frame"],
            "to": min(start + _frames(group.end, fps) + CAPTION_HOLD_FRAMES, end),
            "words": entries,
        })
    for current, following in zip(out, out[1:]):
        current["to"] = following["from"]
    for group in out:
        group["to"] = max(group["to"], group["from"] + 1)
    return out


def build_render_props(plan: Plan, fps: int = 30, project_dir: Path | None = None) -> dict:
    for scene in plan.scenes:
        if scene.audio is None:
            raise ValueError(f"cena {scene.id} sem narração")
        tokens = [t for t in tokenize(scene.narration) if normalize_token(t)]
        if (
            scene.audio.text_hash != text_hash(scene.narration, plan.voice)
            or len(scene.audio.words) != len(tokens)
        ):
            raise ValueError(
                f"cena {scene.id}: narração desatualizada (o texto ou a voz mudou); gere a narração de novo"
            )
        if scene.media and project_dir and not (Path(project_dir) / scene.media).is_file():
            raise ValueError(f"cena {scene.id}: arquivo de mídia não encontrado: {scene.media}")

    gap = plan.voice.scene_gap_seconds
    durations = [_frames(s.audio.duration + gap, fps) for s in plan.scenes]
    durations[-1] += _frames(TAIL_SECONDS, fps)
    starts = [sum(durations[:i]) for i in range(len(durations))]
    total = sum(durations)

    scenes: list[dict] = []
    groups: list[dict] = []
    sfx: list[dict] = []
    for index, (scene, start, length) in enumerate(zip(plan.scenes, starts, durations)):
        actions = _scene_actions(scene, fps)
        scenes.append({
            "id": scene.id,
            "component": scene.component,
            "props": scene.props,
            "from": start,
            "durationInFrames": length,
            "camera": scene.camera,
            "transition": scene.transition,
            "media": scene.media,
            "audio": scene.audio.file,
            "actions": actions,
        })
        groups.extend(_scene_captions(plan, scene, start, start + length, fps))
        if not scene.sfx.enabled:
            continue
        if index > 0 and scene.transition != "cut":
            sfx.append({"name": "whoosh", "frame": max(start - WHOOSH_LEAD_FRAMES, 0), "db": SFX_DB})
        for action in actions:
            name = action_sfx(scene.component, action["do"])
            if name:
                sfx.append({"name": name, "frame": start + action["frame"], "db": SFX_DB})
    sfx.sort(key=lambda item: item["frame"])

    music = None
    music_path = resolve_music(plan, project_dir)
    if music_path is not None:
        music = {
            "src": f"music/{music_path.name}",
            "loop": probe_duration(music_path) < total / fps,
            "envelope": _envelope(plan, starts, total, fps),
            "fadeInFrames": _frames(plan.music.fade_in, fps),
            "fadeOutFrames": _frames(plan.music.fade_out, fps),
        }

    settings = plan.captions
    return {
        "fps": fps,
        "width": WIDTH,
        "height": HEIGHT,
        "durationInFrames": total,
        "scenes": scenes,
        "captions": {
            "enabled": settings.enabled,
            "yPercent": settings.y_percent,
            "fontSize": settings.font_size,
            "highlightColor": settings.highlight_color,
            "groups": groups,
        },
        "music": music,
        "sfx": sfx,
    }
