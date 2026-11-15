import aiohttp
import pytest

from .commercial_support import one_second_mp3, project  # noqa: F401  (fixtures)

from app.services.commercial import narration
from app.services.commercial.__main__ import main
from app.services.commercial.captions import tokenize
from app.services.commercial.schema import load_plan, save_plan


class FakeTTS:
    """Dublê do edge_tts.Communicate: devolve áudio real e uma fronteira por token."""

    calls: list[str] = []
    audio: bytes = b""
    fail_with: Exception | None = None

    def __init__(self, text, voice, *, rate="+0%", boundary="SentenceBoundary", proxy=None, **_):
        self.text, self.voice, self.rate, self.boundary = text, voice, rate, boundary

    async def stream(self):
        type(self).calls.append(self.text)
        if type(self).fail_with is not None:
            raise type(self).fail_with
        yield {"type": "audio", "data": type(self).audio}
        tokens = tokenize(self.text)
        step = 0.9 / len(tokens)
        for i, token in enumerate(tokens):
            yield {
                "type": "WordBoundary",
                "offset": int(i * step * 1e7),
                "duration": int(step * 0.8 * 1e7),
                "text": token.strip(".,!?"),
            }


@pytest.fixture
def fake_tts(monkeypatch, one_second_mp3):
    FakeTTS.calls = []
    FakeTTS.audio = one_second_mp3
    FakeTTS.fail_with = None
    monkeypatch.setattr(narration.edge_tts, "Communicate", FakeTTS)
    monkeypatch.setattr(narration, "RETRY_DELAYS", (0, 0))
    return FakeTTS


def test_narrate_writes_audio_and_words(project, fake_tts):
    plan = narration.narrate_project(project)
    assert plan.status.narration == "done"
    first = plan.scenes[0]
    assert (project / first.audio.file).stat().st_size > 1000
    assert first.audio.file == f"audio/{first.id}.mp3"
    assert first.audio.duration == pytest.approx(1.0, abs=0.1)
    assert [w.text for w in first.audio.words][:3] == ["Você", "pode", "vender"]
    assert first.audio.raw_words[0].start == 0.0
    assert load_plan(project).scenes[-1].audio is not None


def test_narrate_uses_voice_settings(project, fake_tts, monkeypatch):
    seen = {}
    original = FakeTTS.__init__

    def spy(self, text, voice, **kwargs):
        seen.update(voice=voice, **kwargs)
        original(self, text, voice, **kwargs)

    monkeypatch.setattr(FakeTTS, "__init__", spy)
    narration.narrate_project(project)
    assert seen["voice"] == "pt-BR-AntonioNeural"
    assert seen["rate"] == "+8%"
    assert seen["boundary"] == "WordBoundary"


def test_narrate_skips_unchanged_scenes(project, fake_tts):
    narration.narrate_project(project)
    count = len(fake_tts.calls)
    narration.narrate_project(project)
    assert len(fake_tts.calls) == count


def test_narrate_redoes_scene_when_text_changes(project, fake_tts):
    narration.narrate_project(project)
    plan = load_plan(project)
    plan.scenes[1].narration = "São 23h47 e chega um áudio."
    plan.scenes[1].emphasis = []
    plan.scenes[1].actions = []
    save_plan(project, plan)
    fake_tts.calls.clear()
    plan = narration.narrate_project(project)
    assert fake_tts.calls == ["São 23h47 e chega um áudio."]
    assert [w.text for w in plan.scenes[1].audio.words][:2] == ["São", "23h47"]


def test_narrate_failure_sets_status(project, fake_tts):
    fake_tts.fail_with = aiohttp.ClientError("conexão recusada")
    with pytest.raises(narration.NarrationError):
        narration.narrate_project(project)
    assert len(fake_tts.calls) == 3
    plan = load_plan(project)
    assert plan.status.narration == "failed"
    assert plan.scenes[0].id in plan.status.errors["narration"]
    assert "conexão recusada" in plan.status.errors["narration"]


def test_total_duration(project, fake_tts):
    plan = narration.narrate_project(project)
    expected = sum(s.audio.duration + 0.25 for s in plan.scenes) + 0.8  # + respiro final
    assert narration.total_duration(plan) == pytest.approx(expected)


def test_cli_reports_total_and_warning(project, fake_tts, capsys):
    assert main(["narrate", str(project)]) == 0
    out = capsys.readouterr().out
    assert "TOTAL" in out
    assert "fora de 30–60 s" in out


def test_cli_returns_1_on_failure(project, fake_tts, capsys):
    fake_tts.fail_with = aiohttp.ClientError("sem rede")
    assert main(["narrate", str(project)]) == 1
    assert "sem rede" in capsys.readouterr().err
