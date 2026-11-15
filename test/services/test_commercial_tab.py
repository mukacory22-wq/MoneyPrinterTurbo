"""Testes da aba de comerciais com o AppTest do Streamlit (sem navegador)."""

import shutil
import threading
import time

import pytest
from streamlit.testing.v1 import AppTest

from app.services.commercial import jobs, pipeline, planner
from app.services.commercial.schema import load_plan, save_plan

from .commercial_support import EXAMPLE


def _app():
    from webui import commercial_tab

    commercial_tab.render(lambda key: key)


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "PROJECTS_ROOT", tmp_path)
    return tmp_path


@pytest.fixture
def demo(root):
    project = root / "demo-clinica"
    shutil.copytree(EXAMPLE, project, ignore=shutil.ignore_patterns("out"))
    return project


def _wait_idle(project, timeout=10.0):
    deadline = time.time() + timeout
    while jobs.is_running(project) and time.time() < deadline:
        time.sleep(0.02)
    assert not jobs.is_running(project)


def _open(project) -> AppTest:
    at = AppTest.from_function(_app, default_timeout=30)
    at.session_state["commercial_pending_project"] = project.name
    at.run()
    assert not at.exception, at.exception
    return at


def _narration_area(at, index):
    return next(w for w in at.text_area if w.key and w.key.endswith(f"_{index}_n"))


def test_new_plan_stays_selected_after_generation(root, monkeypatch):
    def fake_plan(brief, plan_id, generate=None):
        plan = load_plan(EXAMPLE).model_copy(update={"id": plan_id, "brief": brief})
        for scene in plan.scenes:
            scene.audio = None
        return plan

    monkeypatch.setattr(planner, "generate_plan", fake_plan)
    at = AppTest.from_function(_app, default_timeout=30)
    at.run()
    at.text_input(key="commercial_topic").input("Agente de IA para clínicas")
    at.text_input(key="commercial_audience").input("donos de clínicas")
    at.button(key="commercial_generate_plan").click().run()
    project = root / "agente-de-ia-para-clinicas"
    _wait_idle(project)
    at.run()
    assert not at.exception, at.exception
    assert at.selectbox(key="commercial_project_select").value == project.name
    assert (project / "plan.json").is_file()
    assert any("Commercial Plan" in m.value for m in at.markdown)


def test_narration_uses_unsaved_edits(demo, monkeypatch):
    from webui import commercial_tab

    seen = []
    monkeypatch.setattr(
        commercial_tab, "_work_narrate",
        lambda project: (lambda log: seen.append(load_plan(project).scenes[0].narration)),
    )
    at = _open(demo)
    _narration_area(at, 0).input("Você pode vender automação por 3 mil reais.")
    at.button(key="commercial_narrate").click().run()
    _wait_idle(demo)
    assert seen == ["Você pode vender automação por 3 mil reais."]
    plan = load_plan(demo)
    assert plan.scenes[0].audio is None  # texto mudou: áudio antigo descartado
    assert plan.scenes[1].audio is not None


def test_moving_a_scene_keeps_unsaved_edits(demo):
    at = _open(demo)
    _narration_area(at, 9).input("Comenta agenda que eu te mando o fluxo.")
    down = next(w for w in at.button if w.key and w.key.endswith("_0_down"))
    down.click().run()
    assert not at.exception, at.exception
    plan = load_plan(demo)
    assert plan.scenes[1].id == "s01-gancho"
    assert plan.scenes[9].narration == "Comenta agenda que eu te mando o fluxo."


def test_invalid_edit_blocks_narration_and_reports(demo, monkeypatch):
    from webui import commercial_tab

    started = []
    monkeypatch.setattr(commercial_tab, "_work_narrate", lambda project: (lambda log: started.append(1)))
    at = _open(demo)
    props = next(w for w in at.text_area if w.key and w.key.endswith("_0_p"))
    props.input("{ isto não é json")
    at.button(key="commercial_narrate").click().run()
    assert started == []
    assert any("JSON" in e.value for e in at.error)


def test_buttons_are_disabled_while_project_job_runs_in_another_session(demo):
    gate = threading.Event()
    jobs.submit(demo, "render", lambda log: gate.wait(10))
    try:
        at = _open(demo)  # sessão nova, sem job próprio
        assert at.button(key="commercial_narrate").disabled
        assert at.button(key="commercial_render").disabled
        assert any("Commercial Step Render" in i.value for i in at.info)
    finally:
        gate.set()
        _wait_idle(demo)


def test_editing_settings_marks_video_as_stale(demo):
    plan = load_plan(demo)
    plan.status.render = "done"
    save_plan(demo, plan)
    at = _open(demo)
    _narration_area(at, 0).input(plan.scenes[0].narration)  # sem mudança real
    emphasis = next(w for w in at.text_input if w.key and w.key.endswith("_0_e"))
    emphasis.input("automação")
    save = next(w for w in at.button if w.key and w.key.startswith("commercial_save_") and "raw" not in w.key)
    save.click().run()
    assert not at.exception, at.exception
    assert load_plan(demo).status.render == "pending"
