"""Contrato Python ↔ Remotion: os fixtures e o exemplo passam na validação zod."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REMOTION = ROOT / "remotion"
FIXTURES = REMOTION / "fixtures"

pytestmark = pytest.mark.skipif(
    shutil.which("npm") is None or not (REMOTION / "node_modules").exists(),
    reason="dependências do Remotion não instaladas (npm --prefix remotion install)",
)


def _validate(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["npm", "run", "--silent", "validate", "--", str(path)],
        cwd=REMOTION, capture_output=True, text=True,
    )


def _fixture_names() -> list[str]:
    return sorted(p.stem for p in FIXTURES.glob("*.json"))


def test_base_fixtures_exist():
    assert {"Hook", "Media"} <= set(_fixture_names())


@pytest.mark.parametrize("name", _fixture_names() or ["Hook"])
def test_fixture_validates(name):
    result = _validate(FIXTURES / f"{name}.json")
    assert result.returncode == 0, result.stdout + result.stderr


def test_invalid_props_rejected(tmp_path):
    data = json.loads((FIXTURES / "Hook.json").read_text(encoding="utf-8"))
    data["scenes"][0]["props"]["inventado"] = 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    result = _validate(bad)
    assert result.returncode == 1
    assert "inventado" in result.stdout + result.stderr


def test_unknown_component_rejected(tmp_path):
    data = json.loads((FIXTURES / "Hook.json").read_text(encoding="utf-8"))
    data["scenes"][0]["component"] = "Hologram"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    assert _validate(bad).returncode == 1
