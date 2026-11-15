"""Testes das correções da revisão final (I1–I7, M1, M2, M6, M9)."""

import json
import shutil
import time

import pytest
from pydantic import ValidationError

from app.services.commercial import jobs, narration, pipeline, planner, render, timeline
from app.services.commercial.schema import Brief, Plan, load_plan, save_plan, validate_plan

from .commercial_support import EXAMPLE


def _example() -> dict:
    return json.loads((EXAMPLE / "plan.json").read_text(encoding="utf-8"))


# --- I4: caminhos de arquivo no plano -------------------------------------

@pytest.mark.parametrize("value", ["../../../config.toml", "/etc/passwd", "audio/../x.mp3", "audio/x.wav"])
def test_audio_file_must_stay_inside_audio_folder(value):
    data = _example()
    data["scenes"][0]["audio"]["file"] = value
    with pytest.raises(ValidationError):
        Plan.model_validate(data)


@pytest.mark.parametrize("value", ["/etc/passwd", "../x.png", "media/../../x.png", "media/..", "x.png"])
def test_media_must_stay_inside_media_folder(value):
    data = _example()
    data["scenes"][0]["media"] = value
    with pytest.raises(ValidationError):
        Plan.model_validate(data)


@pytest.mark.parametrize("value", ["/etc/hostname", "../segredo.mp3", "resource/songs/../../config.toml", "outra/pasta.mp3"])
def test_music_file_must_be_project_music_or_bundled_song(value):
    data = _example()
    data["music"]["file"] = value
    with pytest.raises(ValidationError):
        Plan.model_validate(data)


def test_music_resolves_inside_project_music(tmp_path):
    (tmp_path / "music").mkdir()
    (tmp_path / "music" / "minha trilha.mp3").write_bytes(b"x")
    data = _example()
    data["music"]["file"] = "music/minha trilha.mp3"
    plan = Plan.model_validate(data)
    assert timeline.resolve_music(plan, tmp_path) == tmp_path / "music" / "minha trilha.mp3"


# --- I5: props normalizados (o que o pydantic aceita, o zod também aceita) --

def test_props_are_normalized_to_declared_types():
    data = _example()
    scene = next(s for s in data["scenes"] if s["component"] == "Stopwatch")
    scene["props"]["total_seconds"] = "41"
    scene["props"]["steps"][0]["at_seconds"] = "6"
    plan = Plan.model_validate(data)
    props = next(s for s in plan.scenes if s.component == "Stopwatch").props
    assert props["total_seconds"] == 41 and props["steps"][0]["at_seconds"] == 6
    assert validate_plan(plan) == []


# --- I6: narração desatualizada e erros de sistema no render ---------------

def test_stale_narration_is_rejected_by_timeline():
    plan = load_plan(EXAMPLE)
    plan.scenes[0].narration = "Texto trocado fora da interface, sem refazer a voz."
    plan.scenes[0].emphasis = []
    plan.scenes[0].actions = []
    with pytest.raises(ValueError, match="narração desatualizada"):
        timeline.build_render_props(plan, project_dir=EXAMPLE)


def test_render_converts_missing_tools_to_render_error(tmp_path, monkeypatch):
    project = tmp_path / "demo"
    shutil.copytree(EXAMPLE, project, ignore=shutil.ignore_patterns("out"))
    plan = load_plan(project)
    plan.status.render = "done"
    save_plan(project, plan)
    monkeypatch.setattr(render.shutil, "which", lambda name: None)
    with pytest.raises(render.RenderError, match="npm"):
        render.render_project(project, log=lambda _: None)
    assert load_plan(project).status.render == "failed"


# --- M1: duração conferida antes de renderizar -----------------------------

def test_total_duration_includes_the_tail():
    plan = load_plan(EXAMPLE)
    expected = sum(s.audio.duration + plan.voice.scene_gap_seconds for s in plan.scenes) + timeline.TAIL_SECONDS
    assert narration.total_duration(plan) == pytest.approx(expected)
    props = timeline.build_render_props(plan, project_dir=EXAMPLE)
    assert props["durationInFrames"] / props["fps"] == pytest.approx(narration.total_duration(plan), abs=0.3)


def test_render_refuses_out_of_range_duration_before_remotion(tmp_path, monkeypatch):
    project = tmp_path / "curto"
    shutil.copytree(EXAMPLE, project, ignore=shutil.ignore_patterns("out"))
    plan = load_plan(project)
    plan.scenes = plan.scenes[:3]
    save_plan(project, plan)
    called = []
    monkeypatch.setattr(render, "render_raw", lambda *a, **k: called.append(1))
    with pytest.raises(render.RenderError, match="fora de 30–60 s"):
        render.render_project(project, log=lambda _: None)
    assert called == []


# --- M2: qualquer mudança no plano invalida o vídeo pronto ------------------

def test_render_status_resets_when_plan_changes():
    old = load_plan(EXAMPLE)
    old.status.render = "done"
    same = old.model_copy(deep=True)
    pipeline.mark_render_stale(old, same)
    assert same.status.render == "done"
    changed = old.model_copy(deep=True)
    changed.captions.font_size = 80
    pipeline.mark_render_stale(old, changed)
    assert changed.status.render == "pending"


# --- M6: o planner não aceita Media nem arquivos inventados -----------------

def test_planner_rejects_media_component_and_drops_media_field():
    brief = Brief(topic="t", audience="a")
    data = {"scenes": [
        {k: s[k] for k in ("id", "narration", "emphasis", "component", "props", "actions")}
        for s in _example()["scenes"]
    ]}
    data["scenes"][1]["media"] = "media/inventado.png"
    plan, errors = planner.parse_plan_response(json.dumps(data), brief, "abc")
    assert errors == [] and plan.scenes[1].media is None
    data["scenes"][0].update(component="Media", props={"fit": "panel"}, actions=[], media="media/x.png")
    plan, errors = planner.parse_plan_response(json.dumps(data), brief, "abc")
    assert plan is None and any("Media" in e for e in errors)


# --- M9: valores fora do formato não entram no plano ------------------------

@pytest.mark.parametrize("path,value", [
    (("voice", "rate"), "fast"), (("captions", "highlight_color"), "azul"),
    (("music", "speech_db"), -80), (("captions", "y_percent"), 150),
])
def test_settings_are_bounded(path, value):
    data = _example()
    data[path[0]][path[1]] = value
    with pytest.raises(ValidationError):
        Plan.model_validate(data)


# --- I3: estado de execução vem do projeto, não do navegador ----------------

def test_is_running_is_per_project(tmp_path):
    import threading

    gate = threading.Event()
    assert jobs.is_running(tmp_path) is False
    jobs.submit(tmp_path, "render", lambda log: gate.wait(5))
    assert jobs.is_running(tmp_path) is True
    gate.set()
    deadline = time.time() + 5
    while jobs.is_running(tmp_path) and time.time() < deadline:
        time.sleep(0.02)
    assert jobs.is_running(tmp_path) is False
