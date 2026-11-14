"""Efeitos sonoros sintetizados com FFmpeg.

Os arquivos ficam versionados em ``remotion/public/sfx``. Um arquivo de mesmo
nome em ``resource/sfx`` (fornecido pelo usuário) tem prioridade.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BUNDLED_DIR = REPO_ROOT / "remotion" / "public" / "sfx"
USER_DIR = REPO_ROOT / "resource" / "sfx"
SAMPLE_RATE = 44100
TARGET_PEAK_DB = -3.0

SFX_DURATIONS: dict[str, float] = {
    "whoosh": 0.45, "click": 0.04, "pop": 0.12, "notify": 0.5,
    "type": 0.03, "impact": 0.8, "shimmer": 0.9,
}
SFX_NAMES: tuple[str, ...] = tuple(SFX_DURATIONS)

# nome -> (fonte lavfi, filtros). {d} = duração, {r} = taxa de amostragem.
_RECIPES: dict[str, tuple[str, str]] = {
    "whoosh": (
        "anoisesrc=color=pink:seed=7:d={d}:r={r}",
        "highpass=f=250,lowpass=f=5000,flanger=delay=3:depth=6:speed=1.2,"
        "afade=t=in:d=0.25:curve=qsin,afade=t=out:st=0.25:d=0.2",
    ),
    "click": ("aevalsrc='sin(2*PI*2500*t)*exp(-120*t)':d={d}:s={r}", "anull"),
    "pop": ("aevalsrc='sin(2*PI*(600*t+2500*t*t))*exp(-18*t)':d={d}:s={r}", "anull"),
    "notify": (
        "aevalsrc='0.6*sin(2*PI*1320*t)*exp(-14*t)"
        "+0.6*gt(t,0.12)*sin(2*PI*1760*(t-0.12))*exp(-9*(t-0.12))':d={d}:s={r}",
        "anull",
    ),
    "type": ("anoisesrc=color=white:seed=11:d={d}:r={r}", "highpass=f=3000,afade=t=out:d={d}"),
    "impact": (
        "aevalsrc='sin(2*PI*55*t)*exp(-5*t)+0.5*sin(2*PI*110*t)*exp(-12*t)':d={d}:s={r}",
        "lowpass=f=400",
    ),
    "shimmer": (
        "aevalsrc='(sin(2*PI*2000*t)+sin(2*PI*2500*t)+sin(2*PI*3150*t))/3"
        "*(0.6+0.4*sin(2*PI*9*t))*sin(PI*t/{d})':d={d}:s={r}",
        "anull",
    ),
}


def _run(args: list[str]) -> str:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-y", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou: {result.stderr[-400:]}")
    return result.stderr


def synthesize(name: str, out_dir: Path) -> Path:
    duration = SFX_DURATIONS[name]
    source, filters = _RECIPES[name]
    source = source.format(d=duration, r=SAMPLE_RATE)
    edge = min(0.005, duration / 4)
    # -12 dB de folga: a medição de pico trabalha em 16 bits e cortaria acima de 0 dB.
    chain = (
        f"{filters.format(d=duration)},afade=t=out:st={duration - edge}:d={edge},"
        "volume=-12dB,aformat=sample_fmts=flt"
    )
    probe = _run(["-f", "lavfi", "-i", source, "-af", f"{chain},volumedetect", "-f", "null", "-"])
    peak = float(re.search(r"max_volume: (-?[\d.]+) dB", probe).group(1))
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{name}.wav"
    _run([
        "-f", "lavfi", "-i", source,
        "-af", f"{chain},volume={TARGET_PEAK_DB - peak:.2f}dB",
        "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", "-t", str(duration), str(out),
    ])
    return out


def synthesize_all(out_dir: Path = BUNDLED_DIR) -> list[Path]:
    return [synthesize(name, Path(out_dir)) for name in SFX_NAMES]


def resolve_sfx(name: str) -> Path:
    if name not in SFX_DURATIONS:
        raise ValueError(f"efeito sonoro desconhecido: {name}")
    override = USER_DIR / f"{name}.wav"
    return override if override.is_file() else BUNDLED_DIR / f"{name}.wav"
