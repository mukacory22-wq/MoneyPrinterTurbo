import json

import pytest

from app.services.commercial import planner
from app.services.commercial.schema import Brief, validate_plan

from .commercial_support import EXAMPLE

BRIEF = Brief(topic="Agente de IA para clínicas", audience="donos de clínicas", target_seconds=50,
              tone="direto", cta="Comente AGENDA")


def _good_response() -> str:
    data = json.loads((EXAMPLE / "plan.json").read_text(encoding="utf-8"))
    scenes = [
        {k: s[k] for k in ("id", "narration", "emphasis", "component", "props", "actions")}
        for s in data["scenes"]
    ]
    return json.dumps({"scenes": scenes}, ensure_ascii=False)


def test_prompt_contains_all_components_and_word_budget():
    prompt = planner.build_planner_prompt(BRIEF)
    for name in planner.PLANNABLE:
        assert f"### {name}" in prompt
    assert "### Media" not in prompt
    assert BRIEF.topic in prompt and BRIEF.audience in prompt and BRIEF.cta in prompt
    assert str(round(50 * planner.WORDS_PER_SECOND)) in prompt
    assert "Corrija" not in prompt


def test_prompt_lists_errors_on_retry():
    prompt = planner.build_planner_prompt(BRIEF, errors=["cena s01: destaque 'x' não está na narração"])
    assert "Corrija" in prompt
    assert "destaque 'x'" in prompt


def test_parse_strips_fences_and_fills_defaults():
    plan, errors = planner.parse_plan_response(f"```json\n{_good_response()}\n```", BRIEF, "meu-plano")
    assert errors == []
    assert plan.id == "meu-plano"
    assert plan.brief == BRIEF
    assert plan.voice.name == "pt-BR-AntonioNeural"
    assert plan.status.plan == "done" and plan.status.narration == "pending"
    assert all(s.audio is None for s in plan.scenes)
    assert validate_plan(plan) == []


def test_parse_accepts_text_around_json():
    plan, errors = planner.parse_plan_response(f"Aqui está:\n{_good_response()}\nEspero que ajude.", BRIEF, "meu-plano")
    assert errors == [] and plan is not None


def test_parse_reports_invalid_json():
    plan, errors = planner.parse_plan_response("não é json", BRIEF, "meu-plano")
    assert plan is None
    assert errors and "JSON" in errors[0]


def test_parse_reports_semantic_errors():
    data = json.loads(_good_response())
    data["scenes"][0]["emphasis"] = ["inexistente"]
    plan, errors = planner.parse_plan_response(json.dumps(data), BRIEF, "meu-plano")
    assert plan is None
    assert any("inexistente" in e for e in errors)


def test_retry_sends_errors_then_succeeds():
    prompts = []

    def generate(prompt):
        prompts.append(prompt)
        return "lixo" if len(prompts) == 1 else _good_response()

    plan = planner.generate_plan(BRIEF, "meu-plano", generate=generate)
    assert len(prompts) == 2
    assert "Corrija" in prompts[1]
    assert plan.id == "meu-plano"


def test_two_failures_raise_with_errors():
    with pytest.raises(planner.PlannerError) as info:
        planner.generate_plan(BRIEF, "meu-plano", generate=lambda _: "lixo")
    assert "JSON" in str(info.value)


def test_llm_error_text_is_reported():
    with pytest.raises(planner.PlannerError, match="Error: chave inválida"):
        planner.generate_plan(BRIEF, "meu-plano", generate=lambda _: "Error: chave inválida")


def test_plannable_components_are_implemented_in_remotion():
    from pathlib import Path

    remotion = Path(__file__).resolve().parents[2] / "remotion"
    registry = (remotion / "src" / "registry.ts").read_text(encoding="utf-8")
    for name in planner.PLANNABLE:
        assert f"  {name}: {{Component:" in registry, name
        assert (remotion / "fixtures" / f"{name}.json").is_file(), name
