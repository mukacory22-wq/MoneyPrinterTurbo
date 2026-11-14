import subprocess

import pytest

from app.services.commercial.schema import Plan
from app.services.commercial.timeline import build_render_props, envelope_db_at


def _words(texts, t0=0.1, step=0.4, dur=0.3):
    return [
        {"text": t, "start": round(t0 + i * step, 3), "end": round(t0 + i * step + dur, 3)}
        for i, t in enumerate(texts)
    ]


def _scene(sid, narration, duration, **extra):
    texts = [t.strip(".,!?") for t in narration.split()]
    scene = {
        "id": sid,
        "narration": narration,
        "component": "Hook",
        "props": {"text": "Oi"},
        "audio": {
            "file": f"audio/{sid}.mp3", "duration": duration,
            "words": _words(texts), "text_hash": "x",
        },
    }
    scene.update(extra)
    return scene


def make_plan(**overrides) -> Plan:
    data = {
        "id": "teste",
        "brief": {"topic": "t", "audience": "a"},
        "music": {"file": None},
        "scenes": [
            _scene("a", "Você pode vender automação.", 2.0, emphasis=["automação"]),
            _scene(
                "b", "Chega um Pix agora.", 3.0,
                component="PhoneLockScreen",
                props={"time": "1:00", "date": "hoje", "notifications": [
                    {"id": "pix", "app": "pix", "title": "Pix", "body": "R$ 1"}]},
                actions=[{"at": "Pix", "do": "show", "target": "pix"}],
            ),
            _scene("c", "Fim.", 1.0, transition="cut"),
        ],
    }
    data.update(overrides)
    return Plan.model_validate(data)


def test_scene_frames_and_tail():
    props = build_render_props(make_plan())
    scenes = props["scenes"]
    assert [s["from"] for s in scenes] == [0, 68, 166]
    assert [s["durationInFrames"] for s in scenes] == [68, 98, 38 + 24]
    assert props["durationInFrames"] == 228
    assert (props["fps"], props["width"], props["height"]) == (30, 1080, 1920)
    assert scenes[0]["audio"] == "audio/a.mp3"


def test_action_frame_from_phrase():
    scene = build_render_props(make_plan())["scenes"][1]
    # "Pix" é a 3ª palavra: start = 0.1 + 2*0.4 = 0.9 s → quadro 27 (relativo à cena)
    assert scene["actions"] == [{"do": "show", "target": "pix", "frame": 27}]


def test_caption_groups_absolute_and_emphasis():
    captions = build_render_props(make_plan())["captions"]
    first = captions["groups"][0]
    assert [w["text"] for w in first["words"]] == ["Você", "pode", "vender"]
    assert first["from"] == 3 and first["words"][1]["frame"] == 15
    second = captions["groups"][1]
    assert second["words"] == [{"text": "automação", "frame": 39, "emphasis": True}]
    assert first["to"] == second["from"]
    third = captions["groups"][2]
    assert third["from"] == 68 + 3
    assert captions["yPercent"] == 60 and captions["highlightColor"] == "#8FB8FF"


def test_caption_group_never_outlives_scene():
    props = build_render_props(make_plan())
    for group in props["captions"]["groups"]:
        assert group["to"] <= props["durationInFrames"]
        assert group["to"] > group["from"]


def test_missing_audio_raises():
    plan = make_plan()
    plan.scenes[1].audio = None
    with pytest.raises(ValueError, match="cena b sem narração"):
        build_render_props(plan)


@pytest.fixture
def music_file(tmp_path):
    out = tmp_path / "trilha.mp3"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=5", str(out)],
        check=True,
    )
    return out


def test_envelope_ducks_during_speech(music_file):
    plan = make_plan(music={"file": str(music_file)})
    music = build_render_props(plan)["music"]
    env = music["envelope"]
    # meio da 2ª palavra da cena a (0.5–0.8 s) → quadro 20
    assert envelope_db_at(env, 20) == pytest.approx(-18)
    # cena b: fala termina em 1.6 s; a cena dura 3.25 s → silêncio no quadro 68+80
    assert envelope_db_at(env, 68 + 80) == pytest.approx(-9)
    # rampa: a meio caminho entre os dois níveis logo após a fala
    assert -18 < envelope_db_at(env, 68 + 54) < -9
    assert all(a["frame"] < b["frame"] for a, b in zip(env, env[1:]))


def test_envelope_fades_and_src(music_file):
    plan = make_plan(music={"file": str(music_file)})
    music = build_render_props(plan)["music"]
    assert music["src"] == "music/trilha.mp3"
    assert music["fadeInFrames"] == 15
    assert music["fadeOutFrames"] == 45


def test_music_loop_flag(music_file):
    plan = make_plan(music={"file": str(music_file)})
    assert build_render_props(plan)["music"]["loop"] is True  # 5 s < 7.6 s
    long_plan = make_plan(
        music={"file": str(music_file)},
        scenes=[_scene("a", "Um.", 1.0), _scene("b", "Dois.", 1.0), _scene("c", "Três.", 1.0)],
    )
    assert build_render_props(long_plan)["music"]["loop"] is False  # 5 s > 4.55 s


def test_no_music():
    assert build_render_props(make_plan())["music"] is None


def test_missing_music_file_raises():
    plan = make_plan(music={"file": "nao/existe.mp3"})
    with pytest.raises(ValueError, match="trilha"):
        build_render_props(plan)


def test_sfx_whoosh_and_actions():
    sfx = build_render_props(make_plan())["sfx"]
    assert {"name": "whoosh", "frame": 62, "db": -12} in sfx  # cena b começa em 68
    assert {"name": "notify", "frame": 68 + 27, "db": -12} in sfx
    # cena c usa transição "cut": sem whoosh
    assert not any(s["name"] == "whoosh" and s["frame"] > 100 for s in sfx)
    assert sfx == sorted(sfx, key=lambda s: s["frame"])


def test_sfx_disabled_per_scene():
    plan = make_plan()
    plan.scenes[1].sfx.enabled = False
    assert build_render_props(plan)["sfx"] == []
