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


def _cmd_sfx(args) -> int:
    from app.services.commercial import sfx

    for path in sfx.synthesize_all():
        print(path)
    return 0


def _cmd_render(args) -> int:
    from app.services.commercial import render

    try:
        final = render.render_project(Path(args.project))
    except render.RenderError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    print(final)
    return 0


def _cmd_verify(args) -> int:
    from app.services.commercial import render

    problems = render.verify(Path(args.file))
    for problem in problems:
        print(f"PROBLEMA: {problem}")
    if not problems:
        print("ok: 1080x1920, 30 fps, H.264 + AAC, 30–60 s, -14 LUFS")
    return 1 if problems else 0


def _cmd_plan(args) -> int:
    from app.services.commercial import planner
    from app.services.commercial.schema import Brief, save_plan

    out = Path(args.out)
    brief = Brief(topic=args.topic, audience=args.audience, target_seconds=args.seconds,
                  tone=args.tone, cta=args.cta)
    try:
        plan = planner.generate_plan(brief, out.name)
    except planner.PlannerError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    save_plan(out, plan)
    for scene in plan.scenes:
        print(f"[{scene.component}] {scene.narration}")
    print(f"{out / 'plan.json'}  ({len(plan.scenes)} cenas)")
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
    sfx = sub.add_parser("sfx", help="sintetiza os efeitos sonoros em remotion/public/sfx")
    sfx.set_defaults(func=_cmd_sfx)
    render = sub.add_parser("render", help="renderiza out/final.mp4 (Remotion + FFmpeg)")
    render.add_argument("project")
    render.set_defaults(func=_cmd_render)
    verify = sub.add_parser("verify", help="confere um MP4 final")
    verify.add_argument("file")
    verify.set_defaults(func=_cmd_verify)
    plan = sub.add_parser("plan", help="gera o plano (roteiro + cenas) com IA")
    plan.add_argument("--topic", required=True)
    plan.add_argument("--audience", required=True)
    plan.add_argument("--seconds", type=int, default=45)
    plan.add_argument("--tone", default="")
    plan.add_argument("--cta", default="")
    plan.add_argument("--out", required=True, help="pasta do projeto (o nome vira o id)")
    plan.set_defaults(func=_cmd_plan)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
