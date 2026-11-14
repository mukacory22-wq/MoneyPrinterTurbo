import subprocess

import pytest

from app.services.commercial import render
from app.services.commercial.schema import load_plan

from .commercial_support import one_second_mp3, project  # noqa: F401  (fixtures)


def _make_video(path, seconds, size="1080x1920", volume="0.02", fps=30):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "lavfi", "-i", f"testsrc2=s={size}:r={fps}:d={seconds}",
         "-f", "lavfi", "-i", f"sine=frequency=330:duration={seconds}",
         "-af", f"volume={volume}", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(path)],
        check=True,
    )
    return path


def test_finalize_hits_target_loudness(tmp_path):
    raw = _make_video(tmp_path / "raw.mp4", 31)
    final = tmp_path / "final.mp4"
    render.finalize(raw, final)
    assert render.verify(final) == []


def test_verify_reports_bad_duration(tmp_path):
    raw = _make_video(tmp_path / "raw.mp4", 10)
    final = tmp_path / "final.mp4"
    render.finalize(raw, final)
    problems = render.verify(final)
    assert any(p.startswith("duração 10.") and "fora de 30–60 s" in p for p in problems)


def test_verify_reports_resolution(tmp_path):
    video = _make_video(tmp_path / "small.mp4", 31, size="720x1280")
    problems = render.verify(video)
    assert any("720x1280" in p for p in problems)


def test_verify_reports_loudness(tmp_path):
    video = _make_video(tmp_path / "quiet.mp4", 31, volume="0.001")
    assert any("LUFS" in p for p in render.verify(video))


def test_stage_links_files(project, one_second_mp3):
    plan = load_plan(project)
    (project / "audio").mkdir()
    (project / "audio" / "s01-gancho.mp3").write_bytes(one_second_mp3)
    public = render.stage_public_dir(project, plan)
    assert (public / "audio" / "s01-gancho.mp3").read_bytes() == one_second_mp3
    assert (public / "sfx" / "whoosh.wav").is_file()
    assert (public / "music" / "output003.mp3").is_file()


def test_render_project_fails_without_narration(project):
    with pytest.raises(render.RenderError, match="sem narração"):
        render.render_project(project, log=lambda _: None)
    plan = load_plan(project)
    assert plan.status.render == "failed"
    assert "sem narração" in plan.status.errors["render"]
