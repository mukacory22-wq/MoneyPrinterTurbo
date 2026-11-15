"""Aba "Comercial cinematográfico" da WebUI.

Fluxo em quatro passos (briefing → plano → narração → render), cada um
reexecutável. Toda a lógica vive em ``app/services/commercial``; aqui só há
interface.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import streamlit as st
from pydantic import ValidationError

from app.services.commercial import assets, jobs, pipeline
from app.services.commercial.components import ACTIONS, PROPS_MODELS
from app.services.commercial.schema import (
    Brief, Plan, load_plan, save_plan, validate_plan,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SONGS_DIR = REPO_ROOT / "resource" / "songs"
VOICES = {
    "Antonio": "pt-BR-AntonioNeural",
    "Francisca": "pt-BR-FranciscaNeural",
    "Thalita": "pt-BR-ThalitaMultilingualNeural",
}
NEW_PROJECT = "__new__"
KEY = "commercial"

Tr = Callable[[str], str]


# ---------------------------------------------------------------------------
# Etapas em segundo plano
# ---------------------------------------------------------------------------

def _work_plan(project: Path, brief: Brief):
    def work(log):
        from app.services.commercial import planner

        log("Gerando roteiro e cenas com IA…")
        plan = planner.generate_plan(brief, project.name)
        save_plan(project, plan)
        log(f"Plano criado: {len(plan.scenes)} cenas.")

    return work


def _work_narrate(project: Path):
    def work(log):
        from app.services.commercial import narration

        log("Gerando narração (Edge TTS)…")
        plan = narration.narrate_project(project)
        for scene in plan.scenes:
            log(f"{scene.id}: {scene.audio.duration:.2f} s")
        log(f"Total: {narration.total_duration(plan):.1f} s")

    return work


def _work_render(project: Path):
    def work(log):
        from app.services.commercial import render

        render.render_project(project, log)

    return work


def _start(project: Path, step: str, work, tr: Tr) -> None:
    try:
        st.session_state[f"{KEY}_job"] = jobs.submit(project, step, work)
    except jobs.JobBusyError:
        st.warning(tr("Commercial Job Busy"))
    else:
        st.rerun()


@st.fragment(run_every=1.0)
def _job_panel(tr: Tr) -> None:
    job_id = st.session_state.get(f"{KEY}_job")
    state = jobs.get(job_id) if job_id else None
    if state is None:
        return
    labels = {
        "plan": tr("Commercial Step Plan"),
        "narrate": tr("Commercial Step Narration"),
        "render": tr("Commercial Step Render"),
    }
    label = labels.get(state.step, state.step)
    if state.status == "running":
        st.info(f"⏳ {label}…")
        if state.logs:
            st.code("\n".join(state.logs[-12:]), language=None)
        return
    # Terminou: mostra o resultado uma vez e recarrega a página inteira.
    st.session_state.pop(f"{KEY}_job", None)
    if state.status == "failed":
        st.session_state[f"{KEY}_flash"] = ("error", f"{label}: {state.error}")
    else:
        st.session_state[f"{KEY}_flash"] = ("success", f"{label}: {tr('Commercial Done')}")
    st.rerun(scope="app")


def _flash() -> None:
    flash = st.session_state.pop(f"{KEY}_flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])


# ---------------------------------------------------------------------------
# Passo 1 — briefing
# ---------------------------------------------------------------------------

def _briefing(tr: Tr, busy: bool) -> None:
    st.markdown(f"#### 1 · {tr('Commercial Briefing')}")
    topic = st.text_input(tr("Commercial Topic"), key=f"{KEY}_topic",
                          placeholder=tr("Commercial Topic Placeholder"))
    audience = st.text_input(tr("Commercial Audience"), key=f"{KEY}_audience",
                             placeholder=tr("Commercial Audience Placeholder"))
    col1, col2, col3 = st.columns([1, 2, 2])
    seconds = col1.slider(tr("Commercial Duration"), 30, 60, 45, key=f"{KEY}_seconds")
    tone = col2.text_input(tr("Commercial Tone"), key=f"{KEY}_tone")
    cta = col3.text_input(tr("Commercial CTA"), key=f"{KEY}_cta")
    if st.button(tr("Commercial Generate Plan"), type="primary", disabled=busy,
                 key=f"{KEY}_generate_plan"):
        if not topic.strip() or not audience.strip():
            st.error(tr("Commercial Briefing Required"))
            return
        brief = Brief(topic=topic.strip(), audience=audience.strip(), target_seconds=seconds,
                      tone=tone.strip(), cta=cta.strip())
        project = pipeline.new_project_dir(brief.topic)
        project.mkdir(parents=True)
        st.session_state[f"{KEY}_project"] = project.name
        _start(project, "plan", _work_plan(project, brief), tr)


# ---------------------------------------------------------------------------
# Passo 2 — plano
# ---------------------------------------------------------------------------

def _save(project: Path, data: dict, tr: Tr) -> bool:
    """Valida e grava. Mostra os erros e devolve False se o plano for inválido."""
    try:
        plan = Plan.model_validate(data)
    except ValidationError as exc:
        for error in exc.errors()[:12]:
            st.error(f"{'.'.join(str(p) for p in error['loc'])}: {error['msg']}")
        return False
    errors = validate_plan(plan)
    if errors:
        for error in errors[:12]:
            st.error(error)
        return False
    pipeline.invalidate_stale(plan)
    save_plan(project, plan)
    return True


def _mutate(project: Path, plan: Plan, change: Callable[[dict], None], tr: Tr) -> None:
    data = plan.model_dump(mode="json")
    change(data)
    if _save(project, data, tr):
        st.rerun()


def _plan_editor(project: Path, plan: Plan, rev: int, tr: Tr, busy: bool) -> None:
    st.markdown(f"#### 2 · {tr('Commercial Plan')}")
    st.caption(f"{plan.brief.topic} — {plan.brief.audience}")
    components = list(PROPS_MODELS)
    edited: list[dict] = []
    parse_errors: list[str] = []

    for index, scene in enumerate(plan.scenes):
        k = f"{KEY}_{project.name}_{rev}_{index}"
        title = f"{index + 1}. [{scene.component}] {scene.narration[:70]}"
        with st.expander(title, expanded=False):
            narration = st.text_area(tr("Commercial Narration Text"), scene.narration, key=f"{k}_n", height=80)
            c1, c2 = st.columns(2)
            component = c1.selectbox(tr("Commercial Component"), components,
                                     index=components.index(scene.component), key=f"{k}_c")
            emphasis = c2.text_input(tr("Commercial Emphasis"), ", ".join(scene.emphasis), key=f"{k}_e",
                                     help=tr("Commercial Emphasis Help"))
            props_text = st.text_area(tr("Commercial Props"),
                                      json.dumps(scene.props, ensure_ascii=False, indent=2),
                                      key=f"{k}_p", height=220)
            actions_text = st.text_area(
                tr("Commercial Actions"),
                json.dumps([a.model_dump() for a in scene.actions], ensure_ascii=False, indent=2),
                key=f"{k}_a", height=140,
                help=f"{tr('Commercial Actions Help')} {', '.join(sorted(ACTIONS[component])) or '—'}",
            )
            media = scene.media
            upload = st.file_uploader(tr("Commercial Media"), key=f"{k}_m",
                                      type=sorted(assets.ALLOWED_EXTENSIONS))
            if media:
                st.caption(f"{tr('Commercial Media Current')}: {media}")
            if upload is not None:
                try:
                    media = assets.import_media(project, scene.id, upload.name, upload.getvalue())
                except assets.AssetError as exc:
                    st.error(str(exc))

            b1, b2, b3, _ = st.columns([1, 1, 1, 5])
            if b1.button("↑", key=f"{k}_up", disabled=busy or index == 0):
                _mutate(project, plan, lambda d, i=index: d["scenes"].insert(i - 1, d["scenes"].pop(i)), tr)
            if b2.button("↓", key=f"{k}_down", disabled=busy or index == len(plan.scenes) - 1):
                _mutate(project, plan, lambda d, i=index: d["scenes"].insert(i + 1, d["scenes"].pop(i)), tr)
            if b3.button("🗑", key=f"{k}_del", disabled=busy or len(plan.scenes) <= 3):
                _mutate(project, plan, lambda d, i=index: d["scenes"].pop(i), tr)

        item = scene.model_dump(mode="json")
        item.update(
            narration=narration.strip(),
            component=component,
            emphasis=[e.strip() for e in emphasis.split(",") if e.strip()],
            media=media,
        )
        try:
            item["props"] = json.loads(props_text or "{}")
            item["actions"] = json.loads(actions_text or "[]")
        except json.JSONDecodeError as exc:
            parse_errors.append(f"{tr('Commercial Scene')} {index + 1}: JSON — {exc}")
        edited.append(item)

    c1, c2 = st.columns([1, 1])
    if c1.button(tr("Commercial Save Plan"), type="primary", disabled=busy, key=f"{KEY}_save_{rev}"):
        if parse_errors:
            for error in parse_errors:
                st.error(error)
        else:
            data = plan.model_dump(mode="json")
            data["scenes"] = edited
            if _save(project, data, tr):
                st.session_state[f"{KEY}_flash"] = ("success", tr("Commercial Plan Saved"))
                st.rerun()
    if c2.button(tr("Commercial Add Scene"), disabled=busy or len(plan.scenes) >= 14, key=f"{KEY}_add_{rev}"):
        def add(data: dict) -> None:
            ids = {s["id"] for s in data["scenes"]}
            number = len(data["scenes"]) + 1
            while f"s{number:02d}-nova" in ids:
                number += 1
            data["scenes"].append({
                "id": f"s{number:02d}-nova", "narration": "Nova cena.", "component": "Hook",
                "props": {"text": "Nova cena"},
            })
        _mutate(project, plan, add, tr)

    with st.expander(tr("Commercial Raw JSON")):
        raw = st.text_area("plan.json", json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2),
                           key=f"{KEY}_raw_{project.name}_{rev}", height=420, label_visibility="collapsed")
        if st.button(tr("Commercial Save Raw JSON"), disabled=busy, key=f"{KEY}_save_raw_{rev}"):
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                st.error(f"JSON — {exc}")
            else:
                if _save(project, data, tr):
                    st.rerun()


# ---------------------------------------------------------------------------
# Passo 3 — narração
# ---------------------------------------------------------------------------

def _narration(project: Path, plan: Plan, rev: int, tr: Tr, busy: bool) -> None:
    from app.services.commercial.narration import total_duration

    st.markdown(f"#### 3 · {tr('Commercial Step Narration')}")
    names = list(VOICES)
    current = next((n for n, v in VOICES.items() if v == plan.voice.name), names[0])
    c1, c2 = st.columns(2)
    voice = c1.selectbox(tr("Commercial Voice"), names, index=names.index(current), key=f"{KEY}_voice_{rev}")
    rate = c2.slider(tr("Commercial Voice Rate"), -20, 40, int(plan.voice.rate.rstrip("%")),
                     format="%d%%", key=f"{KEY}_rate_{rev}")
    if st.button(tr("Commercial Generate Narration"), type="primary", disabled=busy, key=f"{KEY}_narrate"):
        data = plan.model_dump(mode="json")
        data["voice"].update(name=VOICES[voice], rate=f"{rate:+d}%")
        if _save(project, data, tr):
            _start(project, "narrate", _work_narrate(project), tr)

    done = [s for s in plan.scenes if s.audio]
    if not done:
        st.caption(tr("Commercial No Narration"))
        return
    total = total_duration(plan)
    pending = len(plan.scenes) - len(done)
    st.write(f"**{tr('Commercial Total Duration')}: {total:.1f} s**"
             + (f" · {pending} {tr('Commercial Scenes Pending')}" if pending else ""))
    if not pending and not 30 <= total <= 60:
        st.warning(tr("Commercial Duration Warning"))
    with st.expander(tr("Commercial Listen Scenes")):
        for scene in done:
            path = project / scene.audio.file
            st.caption(f"{scene.id} · {scene.audio.duration:.2f} s — {scene.narration}")
            if path.is_file():
                st.audio(path.read_bytes(), format="audio/mpeg")


# ---------------------------------------------------------------------------
# Passo 4 — render
# ---------------------------------------------------------------------------

def _render(project: Path, plan: Plan, rev: int, tr: Tr, busy: bool) -> None:
    st.markdown(f"#### 4 · {tr('Commercial Step Render')}")
    none_label = tr("Commercial No Music")
    songs = sorted(p.name for p in SONGS_DIR.glob("*.mp3")) if SONGS_DIR.is_dir() else []
    options = [none_label] + [f"resource/songs/{name}" for name in songs]
    current = plan.music.file or none_label
    if current not in options:
        options.append(current)
    c1, c2, c3 = st.columns([2, 1, 1])
    music = c1.selectbox(tr("Commercial Music"), options, index=options.index(current), key=f"{KEY}_music_{rev}")
    speech_db = c2.slider(tr("Commercial Music Speech Volume"), -30, -6, int(plan.music.speech_db),
                          format="%d dB", key=f"{KEY}_sdb_{rev}")
    gap_db = c3.slider(tr("Commercial Music Gap Volume"), -24, 0, int(plan.music.gap_db),
                       format="%d dB", key=f"{KEY}_gdb_{rev}")
    upload = st.file_uploader(tr("Commercial Music Upload"), type=["mp3", "wav", "m4a"], key=f"{KEY}_mup_{rev}")
    c4, c5, c6 = st.columns(3)
    captions_on = c4.checkbox(tr("Commercial Captions"), plan.captions.enabled, key=f"{KEY}_cap_{rev}")
    y_percent = c5.slider(tr("Commercial Captions Position"), 40, 90, int(plan.captions.y_percent),
                          format="%d%%", key=f"{KEY}_capy_{rev}")
    font_size = c6.slider(tr("Commercial Captions Size"), 40, 96, int(plan.captions.font_size),
                          key=f"{KEY}_caps_{rev}")

    ready = all(s.audio for s in plan.scenes)
    if not ready:
        st.caption(tr("Commercial Render Needs Narration"))
    if st.button(tr("Commercial Render"), type="primary", disabled=busy or not ready, key=f"{KEY}_render"):
        data = plan.model_dump(mode="json")
        music_file = None if music == none_label else music
        if upload is not None:
            target = project / "music" / Path(upload.name).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(upload.getvalue())
            music_file = f"music/{target.name}"
        data["music"].update(file=music_file, speech_db=speech_db, gap_db=gap_db)
        data["captions"].update(enabled=captions_on, y_percent=y_percent, font_size=font_size)
        if _save(project, data, tr):
            _start(project, "render", _work_render(project), tr)

    final = project / "out" / "final.mp4"
    if plan.status.render == "done" and final.is_file():
        left, right = st.columns([1, 2])
        left.video(final.read_bytes())
        right.success(tr("Commercial Video Ready"))
        right.download_button(tr("Commercial Download Video"), final.read_bytes(),
                              file_name=f"{project.name}.mp4", mime="video/mp4", key=f"{KEY}_dl_mp4")
        srt = project / "out" / "final.srt"
        if srt.is_file():
            right.download_button(tr("Commercial Download SRT"), srt.read_bytes(),
                                  file_name=f"{project.name}.srt", mime="text/plain", key=f"{KEY}_dl_srt")
    elif plan.status.render == "failed" and plan.status.errors.get("render"):
        st.error(plan.status.errors["render"])


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------

def render(tr: Tr) -> None:
    """Desenha a aba inteira."""
    st.markdown(f"### {tr('Commercial Video Tab')}")
    st.caption(tr("Commercial Intro"))
    _flash()

    projects = pipeline.list_projects()
    names = [NEW_PROJECT] + [p.name for p in projects]
    selected = st.session_state.get(f"{KEY}_project", NEW_PROJECT)
    if selected not in names:
        # projeto recém-criado ainda sem plano (job em andamento) continua selecionado
        names.append(selected)
    choice = st.selectbox(
        tr("Commercial Project"), names, index=names.index(selected),
        format_func=lambda n: tr("Commercial New Project") if n == NEW_PROJECT else n,
        key=f"{KEY}_project_select",
    )
    if choice != selected:
        st.session_state[f"{KEY}_project"] = choice
        st.rerun()

    job = jobs.get(st.session_state.get(f"{KEY}_job", ""))
    busy = job is not None and job.status == "running"
    _job_panel(tr)

    if choice == NEW_PROJECT:
        _briefing(tr, busy)
        return

    project = pipeline.PROJECTS_ROOT / choice
    plan_file = project / "plan.json"
    if not plan_file.is_file():
        if not busy:
            st.warning(tr("Commercial Project Without Plan"))
        return
    try:
        plan = load_plan(project)
    except (ValidationError, ValueError) as exc:
        st.error(f"plan.json: {exc}")
        return
    rev = int(plan_file.stat().st_mtime * 1000)

    _plan_editor(project, plan, rev, tr, busy)
    st.divider()
    _narration(project, plan, rev, tr, busy)
    st.divider()
    _render(project, plan, rev, tr, busy)
