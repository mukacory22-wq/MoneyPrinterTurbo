import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "commercials" / "demo-clinica"


@pytest.fixture(scope="session")
def one_second_mp3(tmp_path_factory) -> bytes:
    out = tmp_path_factory.mktemp("audio") / "tone.mp3"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         "-ar", "24000", "-ac", "1", "-b:a", "48k", str(out)],
        check=True,
    )
    return out.read_bytes()


@pytest.fixture
def project(tmp_path) -> Path:
    """Cópia do projeto de exemplo sem narração gerada."""
    import json

    target = tmp_path / "demo-clinica"
    target.mkdir()
    data = json.loads((EXAMPLE / "plan.json").read_text(encoding="utf-8"))
    for scene in data["scenes"]:
        scene["audio"] = None
    data["status"] = {"plan": "done", "narration": "pending", "render": "pending", "errors": {}}
    (target / "plan.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return target
