"""Importação de imagens e vídeos externos para um projeto de comercial."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
VIDEO_EXTENSIONS = {"mp4", "mov", "webm"}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


class AssetError(ValueError):
    """O arquivo enviado não pode ser usado como mídia de cena."""


def _has_picture(path: Path) -> bool:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height", "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return False
    streams = json.loads(result.stdout or "{}").get("streams") or []
    return bool(streams and streams[0].get("width") and streams[0].get("height"))


def import_media(project_dir: Path, scene_id: str, filename: str, data: bytes) -> str:
    """Valida e copia a mídia para ``media/``. Devolve o caminho relativo ao projeto."""
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in ALLOWED_EXTENSIONS:
        raise AssetError(
            f"formato não aceito: {filename} (use {', '.join(sorted(ALLOWED_EXTENSIONS))})"
        )
    media_dir = Path(project_dir) / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()[:8]
    target = media_dir / f"{scene_id}-{digest}.{extension}"

    fd, tmp = tempfile.mkstemp(dir=media_dir, suffix=f".{extension}")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        if not _has_picture(Path(tmp)):
            raise AssetError(f"arquivo não é imagem/vídeo válido: {filename}")
        os.replace(tmp, target)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return f"media/{target.name}"
