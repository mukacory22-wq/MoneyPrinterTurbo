# Gerador de comerciais cinematográficos — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerador reutilizável que transforma tema + público em um comercial vertical 1080x1920 (30–60 s) com narração Edge TTS, legendas palavra a palavra, painéis de interface animados, trilha com ducking, SFX e MP4 final normalizado.

**Architecture:** Python (`app/services/commercial/`) cria e mantém `plan.json`, gera narração e calcula **toda** a linha do tempo (quadros de cenas, palavras, ações, legendas, envelope da trilha, SFX) em um objeto `RenderProps`. O Remotion (`remotion/`) só desenha esse objeto (imagem + áudio). O FFmpeg normaliza e verifica o MP4. A WebUI ganha uma aba que chama o pipeline.

**Tech Stack:** Python 3.11+ · pydantic v2 · edge_tts 7.2.7 · FFmpeg/ffprobe · Node 22 · Remotion 4 (React 18/19, TypeScript, zod) · Streamlit · pytest · GitHub Actions.

**Spec:** `docs/commercial-video/design.md`

## Global Constraints

- Saída: 1080x1920, 30 fps, H.264 + AAC, duração 30–60 s, −14 LUFS (±1), pico ≤ −1 dBTP, `+faststart`.
- Nada simulado no produto: falha de TTS/LLM/render/mídia = erro com causa, nunca conteúdo falso. (Dublês só em testes unitários.)
- Narração somente via Edge TTS; voz padrão `pt-BR-AntonioNeural`, `rate` `+8%`, `scene_gap_seconds` 0.25.
- Trilha: `speech_db` −18, `gap_db` −9, rampas 200 ms, `fade_in` 0.5 s, `fade_out` 1.5 s. SFX −12 dB relativos à voz.
- Legendas: `max_words` 4, `max_chars` 18, quebra em pausa > 250 ms e pontuação, `y_percent` 68, `font_size` 64, `highlight_color` `#8FB8FF`.
- Cores: fundo `#07080A`, painel `#16181C`, papel `#EDE9DF`, borda `rgba(255,255,255,.08)`, raio 28px.
- Fontes locais via `@fontsource` (Inter, Instrument Serif itálico, Caveat). Nenhum asset baixado em tempo de render.
- Componentes recebem 100% do conteúdo por `props`; nenhuma marca/texto fixo de cliente.
- Projetos em `storage/commercials/<id>/` (gitignored); exemplos versionados em `examples/commercials/<id>/`.
- Remotion usa o navegador de `REMOTION_BROWSER_EXECUTABLE` se definido (neste ambiente: `/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell`).
- Testes: `uv run python -X utf8 -m pytest -q test/services/test_commercial_*.py` ; Node: `npm --prefix remotion run typecheck`.
- Textos de UI via `tr()` com chaves em `webui/i18n/pt.json` e `en.json`.

## Review Focus

1. **Números/símbolos na narração** ("R$ 3.000", "11h47", "24h", "Dra.") — alinhamento deve funcionar e a legenda mostrar a grafia original. → teste com fronteiras **reais** do Edge TTS na Task 4.
2. **Frase de destaque/ação com caixa, acento ou pontuação diferente, ou repetida** — casa a primeira ocorrência normalizada; ausente → erro de validação. → Task 2 (`find_phrase`) e Task 1 (`validate_plan`).
3. **Trilha mais curta ou mais longa que o vídeo** — curta repete em loop; longa é cortada com fade-out. → Task 5 (envelope) e Task 10 (render).
4. **Mídia externa** (horizontal, vertical, vídeo com áudio, arquivo inválido) — preenche o painel com `cover`, vídeo sem som, arquivo inválido rejeitado com mensagem. → Task 7 (componente) e Task 12 (`assets.py`).
5. **Narração longa demais** (total > 60 s) ou curta (< 30 s) — narração conclui e informa o total; `verify` reprova o MP4 com a duração na mensagem. → Task 3 e Task 10.

---

## Mapa de arquivos

```
app/services/commercial/
  __init__.py
  __main__.py      # CLI: narrate | props | render | verify | plan
  schema.py        # Plan e submodelos, load/save, validate_plan
  components.py    # modelos pydantic de props por componente + ACTIONS + ids
  captions.py      # normalize_token, align_words, find_phrase, group_captions, to_srt
  narration.py     # Edge TTS por cena
  timeline.py      # build_render_props (toda a matemática de tempo)
  sfx.py           # síntese e resolução de SFX
  render.py        # staging, chamada ao Remotion, loudnorm, verify
  planner.py       # prompt, parse, generate_plan
  assets.py        # importação/validação de mídia
  jobs.py          # execução em segundo plano + log para a WebUI
remotion/
  package.json, tsconfig.json, remotion.config.ts
  src/index.ts, Root.tsx, Commercial.tsx, types.ts, registry.ts
  src/lib/actions.ts, src/lib/anim.ts, src/lib/icons.tsx
  src/fx/Background.tsx, Panel3D.tsx, Camera.tsx, SceneTransition.tsx
  src/captions/Captions.tsx
  src/audio/Soundtrack.tsx
  src/scenes/<Componente>.tsx      # exporta `schema` (zod) e o componente
  scripts/validate-props.ts        # valida um props.json com zod
  fixtures/<Componente>.json       # RenderProps mínimos de 1 cena por componente
  public/sfx/*.wav
webui/commercial_tab.py
webui/Main.py                       # só registra a aba
examples/commercials/demo-clinica/plan.json (+ audio/ gerado pelo CI)
.github/workflows/commercial-narration.yml
test/services/test_commercial_*.py
```

---

### Task 1: Schema do plano e modelos de props

**Files:**
- Create: `app/services/commercial/__init__.py`, `schema.py`, `components.py`
- Create: `examples/commercials/demo-clinica/plan.json`
- Test: `test/services/test_commercial_schema.py`

**Interfaces:**
- Produces:
  - `schema.Word(text: str, start: float, end: float)`
  - `schema.SceneAudio(file: str, duration: float, words: list[Word], text_hash: str, raw_words: list[Word])`
  - `schema.Action(at: str, do: str, target: str | None = None)`
  - `schema.SceneSfx(enabled: bool = True)`
  - `schema.Scene(id, narration, emphasis: list[str] = [], component: ComponentName, props: dict, actions: list[Action] = [], camera: Literal["push_in","drift","static"]="push_in", transition: Literal["blur_zoom","morph","cut"]="blur_zoom", sfx: SceneSfx, media: str | None = None, audio: SceneAudio | None = None)`
  - `schema.Brief(topic, audience, target_seconds: int = 45 (30..60), tone: str = "", cta: str = "")`, `VoiceSettings(provider: Literal["edge"]="edge", name="pt-BR-AntonioNeural", rate="+8%", scene_gap_seconds=0.25)`, `MusicSettings(file: str | None, speech_db=-18, gap_db=-9, fade_in=0.5, fade_out=1.5)`, `CaptionSettings(enabled=True, max_words=4, max_chars=18, y_percent=60, font_size=64, highlight_color="#8FB8FF")`
  - `schema.StepStatus = Literal["pending","done","failed"]`; `schema.Status(plan, narration, render: StepStatus, errors: dict[str, str])`
  - `schema.Plan(version: Literal[1], id: str (slug ^[a-z0-9-]{3,64}$), brief, voice, music, captions, scenes: list[Scene] (3..14), status)`
  - `schema.load_plan(project_dir: Path) -> Plan`, `schema.save_plan(project_dir: Path, plan: Plan) -> None` (escrita atômica: temp + `os.replace`)
  - `schema.validate_plan(plan: Plan) -> list[str]` (erros semânticos legíveis, vazio = ok)
  - `components.ComponentName` (Literal com os 17 nomes), `components.PROPS_MODELS: dict[str, type[BaseModel]]`, `components.ACTIONS: dict[str, set[str]]`, `components.target_ids(component: str, props: dict) -> set[str]`, `components.REVEAL_ACTIONS = {"show","typing","comment","reveal","type"}`

Props (todos `model_config = extra="forbid"`; itens com `id: str` são alvos de ação; `AppIcon = Literal["whatsapp","calendar","pix","alarm","ai","mic","maps","sheets","instagram","bell","generic"]`):

| Componente | Props | Ações |
|---|---|---|
| Hook | `text` | — |
| Media | `fit: Literal["panel","fullscreen"]="panel"` (arquivo vem de `scene.media`, obrigatório) | — |
| PhoneLockScreen | `time, date, alarm: {id,label,sub}\|None, notifications: [{id, app: AppIcon, title, body, meta=""}]` | show, press |
| WhatsAppChat | `contact: {name, subtitle}, messages: [{id, sender: Literal["them","me"], kind: Literal["text","audio"], text="", audio_seconds=0, time}], composer: Literal["idle","recording"]="idle"` | show, typing, play |
| AgentFlow | `title, toggle_off: str, toggle_on: str, steps: [{id, icon: AppIcon, title, subtitle}], dial_label="24h", counter: {label, start: int, end: int}` | activate, toggle, count |
| Calendar | `title, date, hours: tuple[int,int], events: [{id, title, start:"HH:MM", end:"HH:MM", kind: Literal["busy","free","break"]}], side: {title, subtitle, options: [{id,label}]}` | scan, show |
| Stopwatch | `total_seconds: int, steps: [{id, at_seconds: int, label}]` | mark |
| SearchResults | `query, results: [{id, name, meta, status, tone: Literal["bad","good","neutral"], button=""}]` | type, highlight |
| Transcription | `title, sender, duration_seconds: int, text, highlight=""` | play, highlight |
| FormCard | `title, subtitle, fields: [{label,value}], section, options: [{id,title,subtitle}]` | write, check |
| TicketCards | `title, subtitle, fields: [{label,value}], cards: [{id,label,value}], chosen_label, stamp_text="CONFIRMADA"` | choose, stamp |
| DataTable | `title, columns: list[str], rows: [{id, cells: list[str]}]` | type |
| MapCard | `place: {name, address}, button="Enviar", sent_label` | route, send |
| ChecklistStatus | `title, header_left, header_right, items: [{id,time,name,pending_label,done_label}]` | done |
| BarChart | `title, badge="", bars: [{id,label,value: float}]` | grow, highlight |
| SocialPost | `account: {name,subtitle}, title, steps: [{id, icon: AppIcon, label}], comments: [{id,user,keyword}], count_label` | reveal, comment |
| DigitalClock | `time_from, time_to: str\|None, footer_left="", footer_right=""` | set |

`validate_plan` regras (cada uma vira uma mensagem `"cena <id>: ..."`): ids de cena únicos; props válidos pelo modelo do componente; `do` ∈ `ACTIONS[component]`; `target` (quando dado) ∈ `target_ids`; `emphasis` e `actions[].at` encontrados na narração via `captions.find_phrase` sobre tokens da narração (Task 2 — nesta task, use uma busca normalizada simples em `schema._phrase_in_text` e troque por `find_phrase` na Task 2); `component == "Media"` exige `media`.

- [ ] **Step 1:** Testes: `test_example_plan_is_valid` (carrega `examples/commercials/demo-clinica/plan.json`, `validate_plan == []`); `test_rejects_unknown_component`; `test_rejects_action_not_allowed` (`do="stamp"` em `Calendar` → mensagem contém `"stamp"`); `test_rejects_unknown_target`; `test_rejects_emphasis_missing_from_narration`; `test_phrase_match_ignores_case_accents_punctuation` (`"Agenda"` casa em `"…consulta a agenda."`, `"3 mil"` casa em `"por 3 mil!"`); `test_media_requires_file`; `test_save_load_roundtrip` (tmp_path).
- [ ] **Step 2:** Rodar → FAIL (módulo inexistente).
- [ ] **Step 3:** Implementar `schema.py` e `components.py`. Escrever `demo-clinica/plan.json` com 9 cenas seguindo a narrativa da referência e usando **apenas** componentes da leva 1 (`Hook`, `PhoneLockScreen` — inclusive para a cena do horário noturno, `WhatsAppChat`, `AgentFlow`, `Calendar`, `Stopwatch`; sem `Media`, pois não há mídia externa no exemplo), clínica fictícia "Clínica Exemplo", ~110–130 palavras de narração total, `status.narration = "pending"`, `music.file = "resource/songs/output003.mp3"`.
- [ ] **Step 4:** Rodar → PASS.
- [ ] **Step 5:** Commit `feat(commercial): plan schema and component props`.

### Task 2: Alinhamento e legendas

**Files:**
- Create: `app/services/commercial/captions.py`
- Modify: `app/services/commercial/schema.py` (usar `find_phrase`)
- Test: `test/services/test_commercial_captions.py`

**Interfaces:**
- Produces:
  - `normalize_token(s: str) -> str` (minúsculas, NFKD sem acentos, remove tudo que não é `[a-z0-9]`)
  - `tokenize(text: str) -> list[str]` (split por espaço; tokens só de pontuação, ex. "—", são anexados ao anterior)
  - `class AlignmentError(ValueError)`
  - `align_words(narration: str, tts_words: list[Word]) -> list[Word]` — um `Word` por token da narração, com grafia original sem pontuação final (`.,!?;:…`)
  - `find_phrase(tokens: list[str], phrase: str) -> tuple[int, int] | None` — índice do primeiro e do último token da 1ª ocorrência
  - `CaptionGroup(words: list[Word], start: float, end: float)` (dataclass)
  - `group_captions(words: list[Word], raw_tokens: list[str], max_words=4, max_chars=18, pause=0.25) -> list[CaptionGroup]` (`raw_tokens` com pontuação, para detectar fim de frase)
  - `to_srt(groups: list[CaptionGroup]) -> str` (tempos absolutos já somados pelo chamador)

Algoritmo de `align_words`: concatenar `normalize_token` de cada token da narração e de cada palavra TTS, guardando o intervalo de caracteres de cada um; `difflib.SequenceMatcher(autojunk=False)` entre as duas strings; se `ratio() < 0.9` → `AlignmentError` citando o primeiro trecho divergente; cada token da narração recebe `start` da primeira palavra TTS cujo intervalo mapeado se sobrepõe e `end` da última; token sem sobreposição herda `end` do anterior como `start`/`end` (duração zero) — se for o primeiro token, `AlignmentError`.

- [ ] **Step 1:** Testes: `test_align_identical_tokens`; `test_align_keeps_original_spelling` (narração `"São 11h47, R$ 3.000!"`, TTS words `["São","11h47","R$","3.000"]` → textos `["São","11h47","R$","3.000"]`); `test_align_tts_splits_token` (narração `"24h"`, TTS `["24","h"]` → 1 palavra com start do 1º e end do 2º); `test_align_raises_on_mismatch`; `test_find_phrase_first_occurrence`; `test_find_phrase_normalized`; `test_group_max_words`; `test_group_max_chars`; `test_group_breaks_on_pause` (gap 0.3 s); `test_group_breaks_on_sentence_end`; `test_to_srt_format` (`"1\n00:00:00,050 --> 00:00:01,200\nVocê pode vender\n"`).
- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** Implementar; trocar `_phrase_in_text` por `find_phrase(tokenize(narration), phrase) is not None`.
- [ ] **Step 4:** Rodar `test_captions.py` e `test_schema.py` → PASS.
- [ ] **Step 5:** Commit `feat(commercial): word alignment and caption grouping`.

### Task 3: Narração Edge TTS + CLI

**Files:**
- Create: `app/services/commercial/narration.py`, `app/services/commercial/__main__.py`
- Test: `test/services/test_commercial_narration.py`

**Interfaces:**
- Consumes: Task 1 `load_plan/save_plan`, Task 2 `align_words`.
- Produces:
  - `async synthesize_scene(text: str, voice: VoiceSettings, out_path: Path) -> tuple[float, list[Word]]` — `edge_tts.Communicate(text, voice.name, rate=voice.rate, boundary="WordBoundary", proxy=os.environ.get("HTTPS_PROXY") or None)`; offset/duração ÷ 1e7; duração do arquivo por ffprobe; até 3 tentativas (espera 1 s, 2 s) só para erros de rede do aiohttp/edge_tts; arquivo vazio → erro.
  - `text_hash(text: str, voice: VoiceSettings) -> str` (sha256 de texto + name + rate, 16 hex)
  - `narrate_project(project_dir: Path, force: bool = False) -> Plan` — para cada cena cujo `audio` é None ou `text_hash` difere: sintetiza em `audio/<scene_id>.mp3`, alinha, grava `SceneAudio(raw_words=…)`; salva o plano após **cada** cena; ao fim `status.narration="done"`; exceção → `status.narration="failed"`, `errors["narration"]="cena <id>: <causa>"`, salva e relança.
  - `total_duration(plan: Plan) -> float` (soma `audio.duration + scene_gap_seconds`)
  - CLI: `python -m app.services.commercial narrate <project_dir> [--force]` imprime `cena  duração  palavras` e `TOTAL xx.xs` + aviso `fora de 30–60 s` quando aplicável; exit 1 em falha.

- [ ] **Step 1:** Testes (dublê de `edge_tts.Communicate` via monkeypatch que emite chunks `audio` com bytes de um MP3 de 1 s gerado por ffmpeg em fixture e `WordBoundary` com offsets): `test_narrate_writes_audio_and_words`; `test_narrate_skips_unchanged_scenes` (contador de chamadas); `test_narrate_redoes_scene_when_text_changes`; `test_narrate_failure_sets_status` (dublê lança `aiohttp.ClientError` 3x → status failed, mensagem com id da cena); `test_cli_reports_total_and_warning` (total < 30 → saída contém `"fora de 30–60 s"`).
- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Rodar → PASS.
- [ ] **Step 5:** Commit `feat(commercial): Edge TTS narration per scene`.

### Task 4: Narração real via GitHub Actions (marco: narração resolvida)

**Files:**
- Create: `.github/workflows/commercial-narration.yml`
- Create (pelo CI): `examples/commercials/demo-clinica/audio/*.mp3`, `plan.json` atualizado
- Test: `test/services/test_commercial_real_narration.py`

Workflow:
```yaml
name: Commercial narration
on:
  push:
    branches: ["ccr-*"]
    paths: ["examples/commercials/**/plan.json", ".github/workflows/commercial-narration.yml"]
permissions:
  contents: write
concurrency: { group: commercial-narration-${{ github.ref }}, cancel-in-progress: false }
jobs:
  narrate:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: sudo apt-get update && sudo apt-get install -y ffmpeg
      - run: pip install edge_tts==7.2.7 pydantic loguru
      - name: Narrate pending projects
        run: |
          for d in examples/commercials/*/; do
            python -c "import json,sys;sys.exit(0 if json.load(open('${d}plan.json'))['status']['narration']!='done' else 1)" \
              && python -m app.services.commercial narrate "$d"
          done
      - name: Commit results
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add examples/commercials
          git diff --cached --quiet || (git commit -m "chore(commercial): narration from CI" && git push)
```
(`app/services/commercial` não pode importar `app.config` nem módulos pesados no caminho de `narrate`; imports pesados ficam dentro das funções que os usam.)

- [ ] **Step 1:** Escrever `test_real_narration.py`, marcado `@pytest.mark.skipif(not (EXAMPLE/"audio").exists())`: `test_demo_narration_is_real` (todo `scene.audio` existe, arquivo MP3 ≥ 5 KB, `ffprobe` duração ≈ `audio.duration` ±0.05, `words` não vazio, `words[-1].end <= duration + 0.05`, `align_words(narration, raw_words)` reproduz `words`); `test_demo_numbers_spelled_as_written` (palavras da cena com "R$"/"h" mostram a grafia da narração — Review Focus 1).
- [ ] **Step 2:** Commit workflow + teste; `git push -u origin ccr-919f8171-lyxy6v`.
- [ ] **Step 3:** Acompanhar a execução (`mcp__github__actions_list` / `actions_get`); em falha ler `get_job_logs`, corrigir, push.
- [ ] **Step 4:** `git pull` do commit do bot; rodar `pytest test/services/test_commercial_real_narration.py -v` → PASS; `python -m app.services.commercial narrate examples/commercials/demo-clinica` local deve imprimir o total **sem** sintetizar (nada pendente). Ouvir não é possível aqui: reportar ao usuário durações e as 10 primeiras palavras com tempos.
- [ ] **Step 5:** Se o total ficar fora de 30–60 s, ajustar a narração do exemplo, push, repetir Steps 3–4.

### Task 5: Linha do tempo (`RenderProps`)

**Files:**
- Create: `app/services/commercial/timeline.py`
- Test: `test/services/test_commercial_timeline.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: `build_render_props(plan: Plan, fps: int = 30) -> dict` (JSON camelCase, contrato com `remotion/src/types.ts`):

```jsonc
{ "fps":30, "width":1080, "height":1920, "durationInFrames":N,
  "scenes":[{ "id","component","props","from","durationInFrames","camera","transition",
              "media": "media/x.png"|null, "audio":"audio/s01.mp3",
              "actions":[{"do","target","frame"}] }],          // frame relativo à cena
  "captions":{ "enabled","yPercent","fontSize","highlightColor",
               "groups":[{"from","to","words":[{"text","frame","emphasis":bool}]}] }, // absolutos
  "music": {"src","loop":bool,"envelope":[{"frame","db"}]} | null,
  "sfx":[{"name","frame","db"}] }
```

Regras fixadas:
- Cena `i`: `from` = soma anterior; `durationInFrames = round((audio.duration + scene_gap_seconds) * fps)`; última cena + `round(0.8 * fps)`. Cena sem `audio` → `ValueError("cena <id> sem narração")`.
- Ação: `frame = round(words[first_idx].start * fps)` via `find_phrase`.
- Legendas: `group_captions` por cena, tempos + início da cena; `emphasis=True` para palavras dentro de algum intervalo de `find_phrase(emphasis)`.
- Fala: intervalos de palavras (absolutos), unidos quando o espaço < 0.4 s, alargados 0.1 s de cada lado. Envelope: `gap_db` fora, `speech_db` dentro, transições lineares de 200 ms (6 quadros); ponto inicial `{0, -60}` subindo até `gap_db` em `fade_in`; últimos `fade_out` s descem a −60.
- `music.loop` = duração do arquivo (ffprobe) < duração do vídeo; `music=None` se `file` é None.
- SFX: cena `i>0` com `transition != "cut"` → `whoosh` em `from - 6`; ação → mapa `show→notify` (PhoneLockScreen) / `pop` (demais), `typing|type|write→type`, `press|check|choose|toggle|activate|mark→click`, `stamp|count|set→impact`, `scan|route|grow|highlight→shimmer`, `send|comment|reveal|done→pop`, `play→` nenhum; `db = -12`; cenas com `sfx.enabled=false` não geram.

- [ ] **Step 1:** Testes com plano sintético (2 cenas, words à mão): `test_scene_frames_and_tail`; `test_action_frame_from_phrase`; `test_caption_groups_absolute_and_emphasis`; `test_envelope_ducks_during_speech` (no meio de uma palavra `db == -18`; num silêncio de 1 s `db == -9`); `test_envelope_fades`; `test_music_loop_flag` (arquivo de 5 s gerado por ffmpeg vs vídeo de 8 s → `loop True`); `test_sfx_whoosh_and_actions`; `test_missing_audio_raises`.
- [ ] **Step 2:** FAIL → **Step 3:** implementar → **Step 4:** PASS.
- [ ] **Step 5:** Adicionar comando CLI `props <project_dir>` (grava `out/props.json`), commit `feat(commercial): render timeline`.

### Task 6: Efeitos sonoros sintetizados

**Files:**
- Create: `app/services/commercial/sfx.py`, `remotion/public/sfx/{whoosh,click,pop,notify,type,impact,shimmer}.wav`
- Test: `test/services/test_commercial_sfx.py`

**Interfaces:**
- Produces: `SFX_NAMES: tuple[str, ...]`; `synthesize_all(out_dir: Path) -> list[Path]`; `resolve_sfx(name: str) -> Path` (prefere `resource/sfx/<name>.wav`, senão `remotion/public/sfx/<name>.wav`).

Receitas `ffmpeg -f lavfi` (44.1 kHz, mono, PCM 16, normalizar pico a −3 dBFS):
- `whoosh` 0.45 s: `anoisesrc=color=pink` → `bandpass` com frequência varrendo 300→3000 Hz (`aeval`/`afreqshift` ou cadeia de `bandpass` + `volume` com envelope `afade` in 0.25/out 0.2)
- `click` 0.04 s: `sine=2500` × envelope exponencial
- `pop` 0.12 s: `sine` 600→1200 Hz (`aevalsrc` chirp) + `afade out`
- `notify` 0.5 s: dois `sine` (1320 Hz 0–0.12 s, 1760 Hz 0.12–0.5 s) com `afade`
- `type` 0.03 s: `anoisesrc=white` + `highpass=3000` + `afade out`
- `impact` 0.8 s: `sine=55` + `anoisesrc` lowpass 200 com decaimento
- `shimmer` 0.9 s: soma de `sine` 2000/2500/3150 Hz com `tremolo` + `afade`

- [ ] **Step 1:** Testes: `test_all_sfx_exist_and_valid` (para cada nome: arquivo existe, 44100 Hz, duração dentro de ±20% da receita, pico entre −4 e −2 dBFS via `astats`); `test_resolve_prefers_user_override` (tmp `resource/sfx` monkeypatchado).
- [ ] **Step 2:** FAIL → **Step 3:** implementar + `python -m app.services.commercial sfx` gera os WAV → **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat(commercial): synthesized sound effects`.

### Task 7: Projeto Remotion — base (fundo, painel, câmera, transições, legendas, áudio, Hook, Media)

**Files:**
- Create: `remotion/package.json`, `tsconfig.json`, `remotion.config.ts`, `src/index.ts`, `Root.tsx`, `Commercial.tsx`, `types.ts`, `registry.ts`, `src/lib/{actions.ts,anim.ts,icons.tsx}`, `src/fx/{Background,Panel3D,Camera,SceneTransition}.tsx`, `src/captions/Captions.tsx`, `src/audio/Soundtrack.tsx`, `src/scenes/{Hook,Media}.tsx`, `scripts/validate-props.ts`, `fixtures/{Hook,Media}.json`, `fixtures/media/test.png` (gerado por `ffmpeg -f lavfi testsrc2=s=1600x900`)
- Modify: `.gitignore` (`remotion/node_modules`, `remotion/out`)
- Test: `test/services/test_commercial_remotion_contract.py`

**Interfaces:**
- Consumes: formato `RenderProps` da Task 5.
- Produces:
  - `types.ts`: `renderPropsSchema` (zod) espelhando o JSON da Task 5; `type RenderProps`.
  - `registry.ts`: `REGISTRY: Record<ComponentName, {Component: React.FC<SceneProps<any>>, schema: z.ZodTypeAny}>`.
  - `SceneProps<P> = { props: P; actions: ResolvedAction[]; durationInFrames: number; mediaSrc: string | null }`.
  - `lib/actions.ts`: `actionFrame(actions, doName, target?) -> number | null`; `progress(frame, fps, startFrame | null, durationInFrames = 12) -> number` (spring 0→1, 0 se null/antes); `isRevealed(actions, target, frame) -> boolean` (true se o alvo não tem ação de revelação ou se já passou do quadro).
  - `fx/Panel3D`: `<Panel3D width? tiltDeg=6 paper=false>` (perspectiva 1600px, deriva senoidal ±1.5° em 6 s, sombra, borda, raio 28).
  - `fx/Camera`: `<Camera mode="push_in"|"drift"|"static" durationInFrames>` (push_in escala 1→1.06; drift translateX −20→20px).
  - `fx/SceneTransition`: entrada 10 quadros (blur 12→0, escala 0.94→1, opacidade) e saída 8 quadros; `cut` sem animação; `morph` sem entrada/saída quando a cena anterior tem o mesmo componente.
  - `Captions`: implementa a seção 7.4 da spec.
  - `Soundtrack`: `<Audio>` por cena (`staticFile(scene.audio)`), música com `volume={f => dbToGain(interp(envelope, f))}` e `loop`, `<Sequence from={sfx.frame}><Audio src={staticFile("sfx/"+name+".wav")} volume={dbToGain(db)}/></Sequence>`.
  - `scripts/validate-props.ts <props.json>`: valida com `renderPropsSchema` e o `schema` de cada cena; imprime erros e sai 1.
  - npm scripts: `typecheck` (`tsc --noEmit`), `validate` (`tsx scripts/validate-props.ts`), `still`, `render`.

- [ ] **Step 1:** `npm --prefix remotion install --save-exact remotion @remotion/cli @remotion/media-utils react react-dom zod @fontsource/inter @fontsource/instrument-serif @fontsource/caveat` e dev `typescript @types/react tsx`; configurar `remotion.config.ts` com `Config.setBrowserExecutable(process.env.REMOTION_BROWSER_EXECUTABLE ?? null)`.
- [ ] **Step 2:** Teste Python `test_hook_and_media_fixtures_validate` (roda `npm --prefix remotion run validate -- fixtures/Hook.json` e `Media.json`, exit 0) e `test_invalid_props_rejected` (fixture com campo extra → exit 1). Rodar → FAIL.
- [ ] **Step 3:** Implementar os arquivos acima.
- [ ] **Step 4:** `npm --prefix remotion run typecheck` → 0 erros; testes → PASS.
- [ ] **Step 5:** `npx remotion still src/index.ts Commercial out/hook-30.png --props=fixtures/Hook.json --frame=30 --public-dir=fixtures` e frames 2, 30 e última-5 de `Media` (horizontal com `cover`); revisar as imagens visualmente contra a referência (grade, partículas, spotlight, vinheta, legenda com destaque) e ajustar até ficar coerente; enviar 1 imagem ao usuário.
- [ ] **Step 6:** Commit `feat(remotion): base composition, captions, soundtrack, Hook and Media`.

### Task 8: Componentes `PhoneLockScreen` e `WhatsAppChat`

**Files:**
- Create: `remotion/src/scenes/{PhoneLockScreen,WhatsAppChat}.tsx`, `remotion/src/fx/Phone.tsx` (moldura de celular 3D: corpo 620x1260, raio 90, ilha dinâmica, reflexo), `fixtures/{PhoneLockScreen,WhatsAppChat}.json`
- Modify: `registry.ts`, `test_remotion_contract.py`

**Interfaces:** Consumes `SceneProps`, `isRevealed`, `progress`, `Phone`, `Panel3D`. Props = tabela da Task 1 (zod com os mesmos campos, `.strict()`).

Comportamento: notificações entram de cima com spring e empilham (mais nova em cima); `press` anima o botão primário do alarme; mensagens WhatsApp: `typing` mostra "digitando…" por 18 quadros e depois o balão; `audio` desenha onda (barras pseudo-aleatórias determinísticas por `id`) e `play` avança o cursor por `audio_seconds`; `composer="recording"` mostra contador e onda no rodapé.

- [ ] **Step 1:** Adicionar ao teste de contrato as duas fixtures → FAIL.
- [ ] **Step 2:** Implementar → `typecheck` e testes PASS.
- [ ] **Step 3:** Stills antes/depois de cada ação de cada fixture; revisão visual; ajustar.
- [ ] **Step 4:** Teste de paridade `test_python_and_zod_agree` (para cada componente registrado: o `props` de cada cena do `demo-clinica/plan.json` passa em pydantic **e** em zod via `validate`).
- [ ] **Step 5:** Commit `feat(remotion): phone lock screen and WhatsApp chat`.

### Task 9: Componentes `AgentFlow`, `Calendar`, `Stopwatch`

**Files:** `remotion/src/scenes/{AgentFlow,Calendar,Stopwatch}.tsx`, fixtures, `registry.ts`, `test_remotion_contract.py`.

Comportamento: `AgentFlow` — etapas apagadas (35%) até `activate` (borda clara + ícone colorido), `toggle` move o interruptor e troca `toggle_off`→`toggle_on`, mostrador 24h com ponteiro girando contínuo, `count` anima o número `start→end` em 24 quadros. `Calendar` — grade de horas `hours`, eventos `busy` sólidos, `break` hachurado, `free` invisíveis até `show`; `scan` faz uma linha de luz percorrer a grade em 30 quadros; opções do painel lateral surgem em `show`. `Stopwatch` — mostrador analógico 0–60 + display digital `mm:ss`, ponteiro vai de 0 a `total_seconds` ao longo da cena; cada step aparece como chip com check em `mark`.

- [ ] **Step 1:** Fixtures no teste de contrato → FAIL. **Step 2:** implementar → PASS + `typecheck`.
- [ ] **Step 3:** Stills e revisão visual. **Step 4:** Commit `feat(remotion): agent flow, calendar and stopwatch`.

### Task 10: Render, finalização e verificação (marco: primeiro MP4)

**Files:**
- Create: `app/services/commercial/render.py`
- Modify: `__main__.py` (`render`, `verify`)
- Test: `test/services/test_commercial_render.py`

**Interfaces:**
- Consumes: Task 5 `build_render_props`, Task 6 `resolve_sfx`, Task 7 scripts.
- Produces:
  - `stage_public_dir(project_dir: Path, plan: Plan) -> Path` — `out/public/` com hardlinks (fallback cópia) de `audio/`, `media/`, `sfx/*.wav` (via `resolve_sfx`), música como `music/<nome>`.
  - `render_raw(project_dir: Path, props_path: Path, public_dir: Path, log: Callable[[str], None]) -> Path` — `npx remotion render src/index.ts Commercial <out/raw.mp4> --props=<…> --public-dir=<…> --codec=h264 --audio-codec=aac --crf=18 --concurrency=<cpu_count>` com `cwd=remotion/`, antes roda `npm run validate`; repassa stdout para `log`; exit ≠ 0 → `RenderError` com as últimas 30 linhas.
  - `finalize(raw: Path, final: Path) -> None` — `loudnorm` 2 passadas (I=−14, TP=−1, LRA=11, `print_format=json`, `measured_*` da 1ª), `-c:v copy -c:a aac -b:a 192k -movflags +faststart`.
  - `verify(final: Path) -> list[str]` — problemas vazios = ok: 1080x1920, 30 fps, h264, aac, 30 ≤ duração ≤ 60, −15 ≤ I ≤ −13 (ebur128), pico verdadeiro ≤ −1.0.
  - `render_project(project_dir: Path, log=print) -> Path` — props → stage → raw → final → verify → `out/final.srt` (`to_srt` dos grupos) → `status.render` done/failed.

- [ ] **Step 1:** Testes: `test_finalize_hits_target_loudness` (MP4 sintético `testsrc2` + `sine` em −30 LUFS → após `finalize`, verify sem problemas exceto duração; usar 31 s); `test_verify_reports_bad_duration` (vídeo 10 s → mensagem contém `"duração 10.0 s"`); `test_verify_reports_resolution`; `test_stage_links_files`.
- [ ] **Step 2:** FAIL → **Step 3:** implementar → **Step 4:** PASS.
- [ ] **Step 5:** E2E real: `python -m app.services.commercial render examples/commercials/demo-clinica` → `verify` sem problemas. Extrair 1 quadro por cena e medir `ebur128` em trecho com fala vs sem fala (diferença da trilha ~9 dB). Revisar os quadros. Enviar `final.mp4` ao usuário (SendUserFile) com o relatório de verificação.
- [ ] **Step 6:** Commit `feat(commercial): render, loudness normalization and verification`.

### Task 11: Planner (roteiro por IA)

**Files:**
- Create: `app/services/commercial/planner.py`, `app/services/commercial/prompts/planner.md`
- Modify: `__main__.py` (`plan --topic --audience --seconds --tone --cta --out`)
- Test: `test/services/test_commercial_planner.py`

**Interfaces:**
- Consumes: Task 1 `Plan`, `validate_plan`, `PROPS_MODELS`, `ACTIONS`.
- Produces: `build_planner_prompt(brief: Brief, errors: list[str] | None = None) -> str`; `parse_plan_response(text: str, brief: Brief, plan_id: str) -> tuple[Plan | None, list[str]]` (remove cercas de código, `json.loads`, completa `version/id/brief/voice/music/captions/status` com padrões, valida; retorna erros pydantic + semânticos); `generate_plan(brief: Brief, plan_id: str, generate: Callable[[str], str] | None = None) -> Plan` (padrão `llm._generate_response`; 1 nova tentativa com os erros; segunda falha → `PlannerError` com a lista).

Prompt (`prompts/planner.md`): papel de roteirista de anúncios verticais pt-BR; estrutura narrativa da spec §2 (gancho→problema→solução→passo a passo→prova→recompensa→bônus opcional→CTA); palavras-alvo `round(target_seconds * 2.4)` ±10%; frases curtas e coloquiais; 6–10 cenas; para cada componente: descrição de 1 linha, JSON Schema de `props` (`model_json_schema()`) e ações permitidas; regras de `emphasis` (1–2 por cena, presentes na narração) e `actions.at` (trecho literal da narração); proibido usar marcas reais; resposta = **somente** o JSON `{ "scenes": [...] }`; em retentativa, anexar "Corrija estes erros:" + lista.

- [ ] **Step 1:** Testes com `generate` dublê: `test_prompt_contains_all_components_and_word_budget`; `test_parse_strips_fences_and_fills_defaults`; `test_retry_sends_errors_then_succeeds`; `test_two_failures_raise_with_errors`.
- [ ] **Step 2:** FAIL → **Step 3:** implementar → **Step 4:** PASS.
- [ ] **Step 5:** Chamada real: com `llm_provider="claude_code"` em `config.toml` local (não versionado), `python -m app.services.commercial plan --topic "Agente de IA que agenda consultas pelo WhatsApp" --audience "donos de clínicas" --seconds 50 --out storage/commercials/teste-ia` → plano válido; mostrar o roteiro ao usuário.
- [ ] **Step 6:** Commit `feat(commercial): AI planner`.

### Task 12: Pipeline, importação de mídia e aba da WebUI

**Files:**
- Create: `app/services/commercial/assets.py`, `app/services/commercial/jobs.py`, `webui/commercial_tab.py`
- Modify: `webui/Main.py` (`_render_application`: após `_render_top_bar()` e diálogos, `standard_tab, commercial_tab = st.tabs([tr("Standard Video Tab"), tr("Commercial Video Tab")], key="main_mode_tabs")`; conteúdo atual dentro de `with standard_tab:`; `with commercial_tab: commercial_tab_module.render(tr)`), `webui/i18n/pt.json`, `webui/i18n/en.json`
- Test: `test/services/test_commercial_assets.py`, `test_jobs.py`

**Interfaces:**
- Produces:
  - `assets.import_media(project_dir: Path, scene_id: str, filename: str, data: bytes) -> str` — extensões `png jpg jpeg webp mp4 mov webm`; `ffprobe` precisa achar stream de vídeo/imagem; grava em `media/<scene_id>-<sha8>.<ext>`; retorna caminho relativo; inválido → `AssetError("arquivo não é imagem/vídeo válido: <nome>")`. Vídeos: Remotion toca com `muted`.
  - `jobs.submit(project_dir: Path, step: Literal["plan","narrate","render"], **kwargs) -> str` (job_id; thread daemon; um job por projeto por vez → `JobBusyError`); `jobs.get(job_id) -> JobState(status: Literal["running","done","failed"], logs: list[str], error: str | None)`.
  - `jobs.narrate` local usa Edge TTS direto (funciona fora deste ambiente de nuvem); erro de rede vira mensagem clara.
  - `commercial_tab.render(tr: Callable[[str], str]) -> None` — 4 passos da spec §10; lista de projetos de `storage/commercials/`; edição de cena (narração, componente, props como JSON, emphasis, ações, upload de mídia); salvar = `validate_plan` + `save_plan`, erros exibidos; status por etapa; polling do job com `st.fragment(run_every=0.5)`; player e downloads de `out/final.mp4` e `out/final.srt`.
- [ ] **Step 1:** Testes: `test_import_valid_image_and_video` (gerados por ffmpeg); `test_import_rejects_invalid_file` (bytes aleatórios `.png`); `test_import_rejects_extension`; `test_job_runs_and_records_logs` (step dublê); `test_job_busy_per_project`.
- [ ] **Step 2:** FAIL → **Step 3:** implementar → **Step 4:** PASS.
- [ ] **Step 5:** Abrir a WebUI (`streamlit run webui/Main.py --server.headless true`), com Playwright: aba aparece, abrir `demo-clinica`, editar uma narração e salvar, disparar render, ver o player. Screenshots ao usuário.
- [ ] **Step 6:** Rodar a suíte inteira `pytest -q test` (sem regressões). Commit `feat(webui): commercial video tab`.

### Task 13: Leva 2 — `SearchResults`, `Transcription`, `FormCard`, `DigitalClock`

**Files:** `remotion/src/scenes/<X>.tsx`, fixtures, `registry.ts`, `test_remotion_contract.py`.

Comportamento: `SearchResults` — `type` digita `query` (1 caractere/2 quadros, cursor piscando), resultados com status colorido por `tone`, `highlight` acende o item. `Transcription` — `play` avança cursor da onda e digita `text` proporcionalmente; `highlight` marca `highlight` com fundo azul. `FormCard` — papel creme, `write` revela `fields.value` em Caveat da esquerda para a direita, `check` marca a opção com traço manuscrito. `DigitalClock` — dígitos de 7 segmentos com brilho; `set` troca `time_from`→`time_to` com piscada.

Cada componente: fixture → teste de contrato FAIL → implementar → PASS + `typecheck` → stills + revisão → commit `feat(remotion): <x>`.

### Task 14: Leva 2 — `TicketCards`, `DataTable`, `MapCard`

Mesmo ciclo da Task 13. `TicketCards`: cartões creme lado a lado, `choose` destaca e reduz os demais, mostra `chosen_label`; `stamp` carimbo com impacto (escala 1.4→1, rotação −8°). `DataTable`: linhas existentes visíveis; linha alvo de `type` digitada célula a célula. `MapCard`: ruas em SVG estilizado, `route` desenha a rota (stroke-dashoffset), `send` mostra `sent_label` com check.

### Task 15: Leva 2 — `ChecklistStatus`, `BarChart`, `SocialPost`

Mesmo ciclo. `ChecklistStatus`: `done` troca `pending_label`→`done_label` com check verde. `BarChart`: `grow` cresce as barras com atraso de 3 quadros entre elas; `highlight` deixa a barra alvo branca e as demais cinza. `SocialPost`: grid de etapas apagadas, `reveal` acende cada uma; `comment` adiciona comentário com selo da `keyword`.

- [ ] **Último step:** Atualizar o prompt do planner (Task 11) — automático via `PROPS_MODELS`; rodar `pytest -q test` e um novo plano real com tema diferente que use componentes da leva 2; renderizar e verificar; enviar MP4 ao usuário. Commit.
