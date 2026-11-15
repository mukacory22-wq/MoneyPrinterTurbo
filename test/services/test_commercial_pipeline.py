from app.services.commercial import narration, pipeline
from app.services.commercial.schema import load_plan, save_plan

from .commercial_support import EXAMPLE


def test_new_project_id_is_slug_and_unique(tmp_path):
    first = pipeline.new_project_dir("Agente de IA p/ Clínicas Odontológicas!", root=tmp_path)
    assert first.name == "agente-de-ia-p-clinicas-odontologicas"
    first.mkdir(parents=True)
    second = pipeline.new_project_dir("Agente de IA p/ Clínicas Odontológicas!", root=tmp_path)
    assert second.name == "agente-de-ia-p-clinicas-odontologicas-2"


def test_new_project_id_handles_empty_and_long_topics(tmp_path):
    assert pipeline.new_project_dir("!!!", root=tmp_path).name == "comercial"
    assert len(pipeline.new_project_dir("palavra " * 40, root=tmp_path).name) <= 48


def test_list_projects_newest_first(tmp_path):
    plan = load_plan(EXAMPLE)
    for name in ("antigo", "recente"):
        save_plan(tmp_path / name, plan.model_copy(update={"id": name}))
    (tmp_path / "sem-plano").mkdir()
    import os
    os.utime(tmp_path / "antigo" / "plan.json", (1, 1))
    assert [p.name for p in pipeline.list_projects(root=tmp_path)] == ["recente", "antigo"]


def test_invalidate_stale_clears_audio_of_edited_scene():
    plan = load_plan(EXAMPLE)
    plan.status.render = "done"
    plan.scenes[2].narration = "Texto novo desta cena."
    changed = pipeline.invalidate_stale(plan)
    assert changed == [plan.scenes[2].id]
    assert plan.scenes[2].audio is None
    assert plan.scenes[1].audio is not None
    assert plan.status.narration == "pending" and plan.status.render == "pending"


def test_invalidate_stale_on_voice_change_clears_all():
    plan = load_plan(EXAMPLE)
    plan.voice.name = "pt-BR-FranciscaNeural"
    assert len(pipeline.invalidate_stale(plan)) == len(plan.scenes)


def test_invalidate_stale_noop_when_unchanged():
    plan = load_plan(EXAMPLE)
    assert pipeline.invalidate_stale(plan) == []
    assert plan.status.narration == "done"
    assert all(
        s.audio.text_hash == narration.text_hash(s.narration, plan.voice) for s in plan.scenes
    )
