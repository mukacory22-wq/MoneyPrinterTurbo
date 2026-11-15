import subprocess

import pytest

from app.services.commercial import assets


def _ffmpeg(args, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, str(out)], check=True)
    return out.read_bytes()


@pytest.fixture
def png_bytes(tmp_path):
    return _ffmpeg(["-f", "lavfi", "-i", "testsrc2=s=1600x900:d=1", "-frames:v", "1"], tmp_path / "a.png")


@pytest.fixture
def mp4_bytes(tmp_path):
    return _ffmpeg(
        ["-f", "lavfi", "-i", "testsrc2=s=720x1280:r=30:d=1", "-f", "lavfi", "-i", "sine=d=1",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest"],
        tmp_path / "a.mp4",
    )


def test_import_valid_image(tmp_path, png_bytes):
    rel = assets.import_media(tmp_path, "s01", "Fachada Clínica.PNG", png_bytes)
    assert rel.startswith("media/s01-") and rel.endswith(".png")
    assert (tmp_path / rel).read_bytes() == png_bytes


def test_import_valid_video(tmp_path, mp4_bytes):
    rel = assets.import_media(tmp_path, "s02", "clipe.mp4", mp4_bytes)
    assert rel.endswith(".mp4") and (tmp_path / rel).is_file()


def test_import_is_stable_for_same_content(tmp_path, png_bytes):
    assert assets.import_media(tmp_path, "s01", "a.png", png_bytes) == assets.import_media(
        tmp_path, "s01", "b.png", png_bytes
    )


def test_import_rejects_invalid_file(tmp_path):
    with pytest.raises(assets.AssetError, match="foto.png"):
        assets.import_media(tmp_path, "s01", "foto.png", b"isto nao e uma imagem" * 50)
    assert not list((tmp_path / "media").glob("*")) if (tmp_path / "media").exists() else True


def test_import_rejects_extension(tmp_path, png_bytes):
    with pytest.raises(assets.AssetError, match="formato"):
        assets.import_media(tmp_path, "s01", "documento.pdf", png_bytes)


def test_import_rejects_audio_only(tmp_path):
    audio = _ffmpeg(["-f", "lavfi", "-i", "sine=d=1", "-c:a", "aac"], tmp_path / "so_audio.mp4")
    with pytest.raises(assets.AssetError):
        assets.import_media(tmp_path, "s01", "so_audio.mp4", audio)
