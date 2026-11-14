"""CLI do gerador de comerciais: python -m app.services.commercial <comando>."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

MIN_SECONDS, MAX_SECONDS = 30, 60


def _cmd_narrate(args) -> int:
    from app.services.commercial import narration

    try:
        plan = narration.narrate_project(Path(args.project), force=args.force)
    except narration.NarrationError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    for scene in plan.scenes:
        print(f"{scene.id:<24} {scene.audio.duration:6.2f}s  {len(scene.audio.words):3d} palavras")
    total = narration.total_duration(plan)
    print(f"TOTAL {total:.1f}s")
    if not MIN_SECONDS <= total <= MAX_SECONDS:
        print(f"AVISO: duração fora de {MIN_SECONDS}–{MAX_SECONDS} s")
    return 0


def _cmd_props(args) -> int:
    import json

    from app.services.commercial.schema import load_plan
    from app.services.commercial.timeline import build_render_props

    project = Path(args.project)
    try:
        props = build_render_props(load_plan(project), project_dir=project)
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    out = project / "out" / "props.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{out}  ({props['durationInFrames'] / props['fps']:.1f}s, {len(props['scenes'])} cenas)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.services.commercial")
    sub = parser.add_subparsers(dest="command", required=True)
    narrate = sub.add_parser("narrate", help="gera a narração (Edge TTS) das cenas pendentes")
    narrate.add_argument("project")
    narrate.add_argument("--force", action="store_true")
    narrate.set_defaults(func=_cmd_narrate)
    props = sub.add_parser("props", help="grava out/props.json (linha do tempo para o Remotion)")
    props.add_argument("project")
    props.set_defaults(func=_cmd_props)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
