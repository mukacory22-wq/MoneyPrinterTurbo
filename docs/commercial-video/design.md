# Gerador de vídeos comerciais cinematográficos — Design

Data: 2026-11-14 · Status: aguardando revisão

## 1. Objetivo

Um gerador **reutilizável** dentro do MoneyPrinterTurbo que, a partir de um tema/produto
e de um público-alvo, produz um comercial vertical (1080x1920, 30 fps, 30–60 s) no estilo
do vídeo de referência ("Agentes de IA — clínica odontológica"): fundo escuro, painéis de
interface realistas flutuando em 3D, legendas palavra a palavra com destaque, narração
pt-BR, trilha com ducking e efeitos sonoros.

Critérios de sucesso:

- O fluxo completo (briefing → plano → narração → render) funciona pela nova aba da WebUI.
- Narração real via Edge TTS; legendas e animações sincronizadas pelos tempos de palavra
  reais retornados pelo Edge TTS.
- MP4 final verificado automaticamente: 1080x1920, 30 fps, H.264 + AAC, 30–60 s,
  −14 LUFS (±1), pico ≤ −1 dBTP.
- Nenhuma funcionalidade simulada: falhas aparecem como erro, nunca como conteúdo falso.

Fora do escopo da v1: legendar narração gravada externamente (exige Whisper/HuggingFace),
modelos 3D Three.js, outros provedores de voz, publicação em redes sociais.

## 2. Referência analisada

`54 s · 720x1280 · 30 fps · −14,1 LUFS integrado`. Só 2 cortes secos detectados; o resto
são fusões/desfoques/morph entre painéis.

- **Narrativa:** gancho com oferta → problema em forma de história → solução → passo a
  passo → prova numérica → recompensa → bônus → CTA ("comente PALAVRA").
- **Visual:** quase monocromático (preto/cinza/branco); cor só em ícones de apps e no
  "papel" creme de fichas/cartões; piso em grade com perspectiva, partículas bokeh,
  spotlight atrás do painel, vinheta; um painel central por cena, leve inclinação 3D.
- **Legendas:** 1–4 palavras, centralizadas abaixo do painel; palavras entram quando
  faladas (desfoque → nítido, cinza → branco); palavra-chave em serifada itálica com caixa
  de seleção azul-clara e alças nos cantos.
- **Sincronia:** a interface reage a palavras específicas (interruptor liga em "24 horas",
  "Urgência" marcada em "urgente", horários surgem em "disponíveis").

## 3. Arquitetura

Abordagem escolhida: **Python orquestra → Remotion renderiza imagem + áudio → FFmpeg
finaliza**.

```
app/services/commercial/
  schema.py      # modelo pydantic do plan.json (fonte única da verdade)
  planner.py     # briefing → plano (via app/services/llm.py)
  narration.py   # Edge TTS por cena + tempos de palavra alinhados ao texto
  captions.py    # agrupamento de legendas, validação de destaques, export .srt
  assets.py      # importação/validação (ffprobe) de imagens e vídeos externos
  sfx.py         # síntese dos efeitos sonoros com FFmpeg
  render.py      # chamada ao Remotion + passe final FFmpeg + verificação
  pipeline.py    # encadeia etapas; refaz qualquer etapa isoladamente
  __main__.py    # CLI interna: plan | narrate | render | verify <projeto>
remotion/                     # projeto Node (React + Remotion 4, TypeScript)
  src/Root.tsx, src/Commercial.tsx
  src/scenes/*.tsx            # um componente por tipo de cena
  src/captions/*.tsx
  src/fx/*.tsx                # fundo, câmera, transições, luz
  src/audio/*.tsx             # narração, trilha com envelope, SFX
  public/fonts, public/sfx
webui/commercial_tab.py       # nova aba Streamlit
storage/commercials/<id>/     # projeto (gitignored)
  plan.json  audio/  media/  out/{final.mp4, final.srt}
examples/commercials/<id>/    # projetos versionados usados no CI de narração
.github/workflows/commercial-narration.yml
```

Fluxo de dados: cada etapa lê `plan.json`, faz seu trabalho, grava de volta. O status de
cada etapa (`pending | done | failed` + mensagem) fica no próprio plano. O Remotion recebe
o plano completo via `--props` e as mídias por caminho relativo ao `public/` (o render
copia/vincula a pasta do projeto para dentro do bundle).

## 4. Formato do plano (`plan.json`, versão 1)

```jsonc
{
  "version": 1,
  "id": "clinica-agente-ia",
  "brief": { "topic": "...", "audience": "...", "target_seconds": 50,
             "tone": "direto, provocativo", "cta": "Comente AGENDA" },
  "voice": { "provider": "edge", "name": "pt-BR-AntonioNeural", "rate": "+8%",
             "scene_gap_seconds": 0.25 },
  "music": { "file": "resource/songs/output003.mp3",
             "speech_db": -18, "gap_db": -9, "fade_in": 0.5, "fade_out": 1.5 },
  "captions": { "enabled": true, "max_words": 4, "max_chars": 18,
                "y_percent": 68, "font_size": 64, "highlight_color": "#8FB8FF" },
  "scenes": [
    {
      "id": "s01-gancho",
      "narration": "Você pode vender automação pra clínica odontológica por 3 mil.",
      "emphasis": ["automação", "3 mil"],
      "component": "PhoneLockScreen",
      "props": { "time": "14:20", "notifications": [
        { "id": "pix", "app": "pix", "title": "Pix recebido", "body": "R$ 3.000,00" } ] },
      "actions": [ { "at": "3 mil", "do": "show", "target": "pix" } ],
      "camera": "push_in",
      "transition": "blur_zoom",
      "sfx": { "enabled": true },
      "media": null,
      "audio": {                      // preenchido pela etapa de narração
        "file": "audio/s01-gancho.mp3", "duration": 3.42,
        "words": [ { "text": "Você", "start": 0.05, "end": 0.29 } ]
      }
    }
  ],
  "status": { "plan": "done", "narration": "pending", "render": "pending",
              "errors": {} }
}
```

Regras de validação:

- `component` deve existir no catálogo; `props` validados pelo schema de cada componente
  (o mesmo schema é espelhado em TypeScript com zod no Remotion).
- `emphasis` e `actions[].at` devem ocorrer no texto de `narration` da própria cena.
- `actions[].target` deve referenciar um `id` existente nos `props`.
- 3 a 14 cenas; narração total estimada coerente com `target_seconds`.

## 5. Catálogo de cenas

| Grupo | Componente | Ações (presas a palavras) |
|---|---|---|
| Celular | `PhoneLockScreen` — hora, alarme, notificações empilhando, Pix | `show`, `press` |
| Celular | `WhatsAppChat` — texto, áudio com onda, digitando, gravando | `show`, `typing`, `play` |
| Painel | `SearchResults` — busca digitando + resultados + mapa | `type`, `highlight` |
| Painel | `AgentFlow` — etapas com ícones, interruptor, mostrador 24h, contador | `activate`, `toggle`, `count` |
| Painel | `Transcription` — onda tocando, texto digitando, trecho destacado | `play`, `highlight` |
| Painel | `FormCard` — ficha em papel, caligrafia, opções marcáveis | `check`, `write` |
| Painel | `Calendar` — agenda do dia, varredura, horários livres | `scan`, `show` |
| Painel | `TicketCards` — cartões de horário, escolha, carimbo CONFIRMADA | `choose`, `stamp` |
| Painel | `DataTable` — planilha, linha sendo digitada | `type` |
| Painel | `MapCard` — mapa, rota, pino, "enviar localização" | `route`, `send` |
| Painel | `ChecklistStatus` — "na fila" → "enviado" | `done` |
| Painel | `BarChart` — barras crescendo, uma destacada | `grow`, `highlight` |
| Painel | `SocialPost` — post com etapas + comentários com palavra-chave | `reveal`, `comment` |
| Objeto | `DigitalClock` — relógio despertador, dígitos mudando | `set` |
| Objeto | `Stopwatch` — cronômetro + linha do tempo de etapas | `mark` |
| Mídia | `Media` — imagem/vídeo externo em painel ou tela cheia | — |
| Texto | `Hook` — frase de impacto para cenas sem painel | — |

Cada componente: dados 100% vindos de `props` (nenhuma marca/conteúdo fixo), estado
derivado de `frame` + tempos das ações (determinístico, sem `useState` temporal).

**Ordem de construção:** leva 1 = `PhoneLockScreen`, `WhatsAppChat`, `AgentFlow`,
`Calendar`, `Stopwatch`, `Media` (+ `Hook`, fundo, legendas, câmera, transições); leva 2 =
os demais, um por vez.

## 6. Estilo visual

- Fundo `#07080A`; piso em grade com perspectiva (linhas 6% branco), partículas bokeh,
  spotlight radial atrás do painel, vinheta, grão sutil.
- Painéis grafite `#16181C`, borda 1px `rgba(255,255,255,.08)`, raio 28px, sombra longa,
  inclinação 3D 4–8° com deriva lenta (`perspective` CSS); papel creme `#EDE9DF`.
- Cores só de ícones (WhatsApp `#25D366` etc.).
- Fontes embutidas via `@fontsource` (licença OFL): Inter (UI/legendas), Instrument Serif
  itálico (destaque), Caveat (manuscrito).
- Animação por `spring()`; câmera: push-in contínuo + reenquadramento suave em ações.
- Transições (10–14 quadros): `blur_zoom` (padrão), `morph` (mesmo componente em cenas
  seguidas), `cut`.

## 7. Legendas

1. Tempos de palavra do Edge TTS (`WordBoundary`: offset/duração em unidades de 100 ns).
2. Alinhamento ao texto do roteiro: tokens do TTS casados com tokens da narração por
   normalização (minúsculas, sem acento/pontuação, números) e distância de edição; a
   legenda exibe a grafia original ("11h47", "R$ 3.000"). Token sem par → etapa falha
   com mensagem indicando a palavra.
3. Agrupamento: ≤ `max_words` e ≤ `max_chars`; quebra em pontuação e pausas > 250 ms;
   não atravessa frase.
4. Render: palavra entra em `start` (desfoque 6px→0, y +8px→0, opacidade 0→1); palavras
   futuras do grupo a 25%; palavra em `emphasis` em serifada itálica com caixa de
   seleção (fundo azul 15%, borda 1px, alças 4px nos cantos).
5. Exporta `final.srt` (por grupo).

## 8. Áudio

- **Narração:** Edge TTS por cena (`pt-BR-AntonioNeural` padrão; Francisca, Thalita
  opcionais; `rate` padrão `+8%`). Duração da cena = duração da fala + `scene_gap_seconds`.
- **Trilha:** `resource/songs/` (29 faixas) ou upload. Envelope de volume calculado dos
  intervalos de fala: `speech_db` durante fala, `gap_db` em pausas, rampas de 200 ms,
  fade-in/out.
- **SFX:** sintetizados com FFmpeg (`sfx.py`) e versionados em `remotion/public/sfx/`:
  `whoosh`, `click`, `pop`, `notify`, `type`, `impact`, `shimmer`. Arquivos de mesmo
  nome em `resource/sfx/` têm prioridade. Disparados por transições e ações; −12 dB
  relativos à voz.
- **Finalização:** Remotion renderiza H.264/AAC com o mix; FFmpeg `loudnorm` em duas
  passadas (I=−14, TP=−1, LRA=11) com `-c:v copy` e `+faststart`; verificação via
  ffprobe + `ebur128`. Fora da tolerância → render marcado `failed`.

## 9. Roteiro (planner)

- Usa `llm.py` (`claude_code` neste ambiente; `anthropic` com chave local do usuário).
- Prompt inclui: briefing, estrutura narrativa da seção 2, catálogo de componentes com o
  schema de `props` e ações, limites de duração (~2,6 palavras/s em pt-BR com `+8%`).
- Saída JSON validada pelo pydantic; em falha, 1 nova tentativa enviando os erros de
  validação ao modelo; segunda falha → erro exibido.

## 10. Aba da WebUI

`webui/commercial_tab.py`, registrada em `Main.py`, textos em `i18n/pt.json` e `en.json`.

1. **Briefing** → "Gerar plano".
2. **Plano** → cenas editáveis (narração, componente, props, destaques, ações, mídia),
   reordenar/apagar/adicionar, editor JSON bruto.
3. **Narração** → voz/velocidade, "Gerar narração", duração por cena e total (aviso fora
   de 30–60 s), player por cena.
4. **Renderizar** → trilha, volumes, legendas; execução em segundo plano no padrão de
   `webui_task`, log ao vivo; player + download de MP4 e SRT.

Lista de projetos existentes para reabrir. Editar a narração de uma cena invalida só o
áudio dessa cena e o render.

## 11. Erros

- Etapas gravam `status` e `errors` no plano; a UI mostra a causa.
- Edge TTS bloqueado/indisponível, mídia inválida, Remotion ou FFmpeg com código ≠ 0 →
  erro com saída relevante. Nunca substituir por conteúdo falso.

## 12. Testes

| Etapa | Como |
|---|---|
| Schema | pytest com planos válidos e inválidos |
| Planner | pytest do prompt/validação + 1 chamada real (`claude_code`) |
| Narração | pytest do alinhamento com dados reais do Edge TTS; geração real via CI |
| Legendas | pytest de agrupamento, destaques e SRT |
| Componentes | `tsc` + `remotion still` em quadros-chave, revisão visual |
| SFX/áudio | pytest: duração/pico dos SFX; envelope medido com `ebur128`/`astats` |
| Ponta a ponta | render completo + verificação automática da seção 8 |

### Narração real via GitHub Actions

O proxy deste ambiente de nuvem não permite WebSocket, que o Edge TTS exige. Por isso:

- `.github/workflows/commercial-narration.yml` roda em `push` **somente** para o branch de
  desenvolvimento, com filtro de caminho `examples/commercials/**/plan.json`.
- Para cada projeto cuja `status.narration` seja `pending`, roda
  `python -m app.services.commercial narrate <projeto>` e faz commit dos MP3 e do
  `plan.json` atualizado de volta no mesmo branch (`permissions: contents: write`).
  Commits feitos com `GITHUB_TOKEN` não disparam novos workflows (sem loop).
- Sem segredos. A sessão de desenvolvimento faz `git pull`, verifica e renderiza
  localmente (Remotion/FFmpeg funcionam aqui).
- No computador do usuário o Edge TTS funciona direto, sem CI.

## 13. Dependências

- Python: as já existentes (`edge_tts`, `pydantic` via FastAPI, `loguru`).
- Node: `remotion`, `@remotion/cli`, `@remotion/transitions`, `@remotion/media-utils`,
  `react`, `react-dom`, `zod`, `@fontsource/inter`, `@fontsource/instrument-serif`,
  `@fontsource/caveat`, `typescript`. Versões fixadas no `package-lock.json`.
- Sistema: FFmpeg/ffprobe, Chromium (Remotion usa o próprio headless shell ou
  `/opt/pw-browsers/chromium`).
- Licença Remotion: gratuita para indivíduos e empresas de até 3 pessoas; acima disso
  exige licença de empresa.
