"""Pequenos utilitários sobre ffprobe/ffmpeg usados pelo gerador de comerciais."""

from __future__ import annotations

import subprocess
from pathlib import Path


def probe_duration(path: Path) -> float:
    """Duração em segundos de um arquivo de mídia (via ffprobe)."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError(f"ffprobe não conseguiu ler {path}: {result.stderr.strip()}")
    return float(result.stdout.strip())
