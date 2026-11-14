"""Confere a narração REAL do projeto de exemplo, gerada pelo Edge TTS.

Pulado se os áudios do exemplo ainda não foram gerados (comando narrate).
"""

import pytest

from app.services.commercial.captions import align_words, tokenize
from app.services.commercial.ffmpeg_utils import probe_duration
from app.services.commercial.schema import load_plan

from .commercial_support import EXAMPLE

pytestmark = pytest.mark.skipif(
    not (EXAMPLE / "audio").exists(), reason="narração do exemplo ainda não gerada"
)


def test_demo_narration_is_real():
    plan = load_plan(EXAMPLE)
    assert plan.status.narration == "done"
    for scene in plan.scenes:
        audio = scene.audio
        assert audio is not None, scene.id
        path = EXAMPLE / audio.file
        assert path.stat().st_size >= 5_000, scene.id
        assert probe_duration(path) == pytest.approx(audio.duration, abs=0.05)
        assert audio.raw_words, scene.id
        assert audio.words[-1].end <= audio.duration + 0.05
        assert all(b.start >= a.start for a, b in zip(audio.words, audio.words[1:])), scene.id
        assert align_words(scene.narration, audio.raw_words) == audio.words


def test_demo_numbers_spelled_as_written():
    plan = load_plan(EXAMPLE)
    by_id = {s.id: s for s in plan.scenes}
    assert "23h47" in [w.text for w in by_id["s02-madrugada"].audio.words]
    assert "9h30" in [w.text for w in by_id["s07-confirma"].audio.words]
    assert "41" in [w.text for w in by_id["s08-tempo"].audio.words]
    for scene in plan.scenes:
        assert len(scene.audio.words) == len(tokenize(scene.narration)), scene.id
