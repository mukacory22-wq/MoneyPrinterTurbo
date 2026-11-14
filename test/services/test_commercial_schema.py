import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.services.commercial import schema
from app.services.commercial.schema import Plan, load_plan, save_plan, validate_plan

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "commercials" / "demo-clinica"


def _example_dict() -> dict:
    return json.loads((EXAMPLE / "plan.json").read_text(encoding="utf-8"))


def _plan(mutate=None) -> Plan:
    data = _example_dict()
    if mutate:
        mutate(data)
    return Plan.model_validate(data)


def test_example_plan_is_valid():
    plan = load_plan(EXAMPLE)
    assert validate_plan(plan) == []
    assert 3 <= len(plan.scenes) <= 14


def test_rejects_unknown_component():
    data = _example_dict()
    data["scenes"][0]["component"] = "Hologram"
    with pytest.raises(ValidationError):
        Plan.model_validate(data)


def _scene_with(data, component):
    return next(s for s in data["scenes"] if s["component"] == component)


def test_rejects_action_not_allowed():
    def mutate(d):
        sc = _scene_with(d, "Calendar")
        sc["actions"].append({"at": sc["actions"][0]["at"], "do": "stamp"})

    errors = validate_plan(_plan(mutate))
    assert any("stamp" in e for e in errors)


def test_rejects_unknown_target():
    def mutate(d):
        sc = _scene_with(d, "Calendar")
        sc["actions"][0]["target"] = "nao-existe"

    errors = validate_plan(_plan(mutate))
    assert any("nao-existe" in e for e in errors)


def test_rejects_emphasis_missing_from_narration():
    def mutate(d):
        d["scenes"][0]["emphasis"] = ["palavrainexistente"]

    errors = validate_plan(_plan(mutate))
    assert any("palavrainexistente" in e for e in errors)


def test_rejects_invalid_props():
    def mutate(d):
        _scene_with(d, "Calendar")["props"]["inventado"] = 1

    errors = validate_plan(_plan(mutate))
    assert any("props" in e for e in errors)


def test_rejects_duplicate_scene_ids():
    def mutate(d):
        d["scenes"][1]["id"] = d["scenes"][0]["id"]

    errors = validate_plan(_plan(mutate))
    assert any("duplicad" in e for e in errors)


def test_phrase_match_ignores_case_accents_punctuation():
    def mutate(d):
        sc = d["scenes"][0]
        sc["narration"] = "Depois ele consulta a agenda. Por 3 mil!"
        sc["emphasis"] = ["Agenda", "3 MIL"]
        sc["actions"] = []

    errors = validate_plan(_plan(mutate))
    assert not any("cena " + "s01" in e and "Agenda" in e for e in errors)
    assert errors == []


def test_media_requires_file():
    def mutate(d):
        sc = d["scenes"][0]
        sc["component"] = "Media"
        sc["props"] = {"fit": "panel"}
        sc["actions"] = []
        sc["media"] = None

    errors = validate_plan(_plan(mutate))
    assert any("media" in e for e in errors)


def test_save_load_roundtrip(tmp_path):
    plan = load_plan(EXAMPLE)
    save_plan(tmp_path, plan)
    again = load_plan(tmp_path)
    assert again == plan
    assert not list(tmp_path.glob("*.tmp"))
