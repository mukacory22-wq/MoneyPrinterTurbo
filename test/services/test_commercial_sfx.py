import json
import re
import subprocess

import pytest

from app.services.commercial import sfx


def _probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate,channels,codec_name:format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    return data["streams"][0], float(data["format"]["duration"])


def _peak_db(path):
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "astats=measure_overall=Peak_level:measure_perchannel=0",
         "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    return float(re.search(r"Peak level dB: (-?[\d.]+)", err).group(1))


def test_names_cover_timeline_mapping():
    from app.services.commercial.timeline import _ACTION_SFX

    assert set(_ACTION_SFX.values()) | {"whoosh", "notify", "pop"} <= set(sfx.SFX_NAMES)


@pytest.mark.parametrize("name", sfx.SFX_NAMES)
def test_bundled_sfx_exist_and_valid(name):
    path = sfx.BUNDLED_DIR / f"{name}.wav"
    assert path.is_file()
    stream, duration = _probe(path)
    assert stream["sample_rate"] == "44100"
    assert stream["codec_name"] == "pcm_s16le"
    assert duration == pytest.approx(sfx.SFX_DURATIONS[name], rel=0.2)
    assert -4.0 <= _peak_db(path) <= -2.0


def test_synthesize_all_writes_every_file(tmp_path):
    paths = sfx.synthesize_all(tmp_path)
    assert sorted(p.name for p in paths) == sorted(f"{n}.wav" for n in sfx.SFX_NAMES)


def test_resolve_prefers_user_override(tmp_path, monkeypatch):
    override = tmp_path / "click.wav"
    override.write_bytes(b"RIFF")
    monkeypatch.setattr(sfx, "USER_DIR", tmp_path)
    assert sfx.resolve_sfx("click") == override
    assert sfx.resolve_sfx("pop") == sfx.BUNDLED_DIR / "pop.wav"


def test_resolve_unknown_name_raises():
    with pytest.raises(ValueError):
        sfx.resolve_sfx("explosao")
