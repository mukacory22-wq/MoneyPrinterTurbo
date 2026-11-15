# Gerador de comerciais cinematográficos

Cria anúncios verticais (1080x1920, 30–60 s) a partir de um tema e de um público:
roteiro por IA, narração Edge TTS, legendas palavra a palavra, painéis de interface
animados, trilha com abaixamento automático nas falas, efeitos sonoros e MP4 final
normalizado em −14 LUFS.

Design completo: [design.md](design.md) · Plano de implementação: [plan.md](plan.md)

## Instalação

Além das dependências normais do MoneyPrinterTurbo (Python + FFmpeg):

```bash
npm --prefix remotion install      # Node 20+ ; instala o Remotion
```

O Remotion baixa um navegador próprio na primeira renderização. Em ambientes sem esse
download, aponte para um Chromium já instalado:

```bash
export REMOTION_BROWSER_EXECUTABLE=/caminho/para/chrome-headless-shell
```

Para o roteiro por IA, configure um provedor em `config.toml` (por exemplo
`llm_provider = "anthropic"` com `anthropic_api_key`, ou `llm_provider = "claude_code"`).

## Pela interface web

`./webui.sh` → no topo da página, escolha **Comercial cinematográfico**.

1. **Briefing** — tema, público, duração, tom e chamada final → *Gerar plano*.
2. **Plano** — edite narração, tipo de cena, conteúdo do painel, palavras de destaque e
   ações; anexe imagem ou vídeo a uma cena; reordene, apague ou adicione cenas.
3. **Narração** — escolha voz e velocidade → *Gerar narração*. A duração real aparece
   por cena e no total.
4. **Renderizar** — escolha a trilha, os volumes e as legendas → *Renderizar vídeo*.
   No fim: player, MP4 e `.srt`.

Os projetos ficam em `storage/commercials/<id>/`.

## Pela linha de comando

```bash
P=storage/commercials/meu-comercial
python -m app.services.commercial plan --topic "..." --audience "..." --seconds 45 \
       --cta "Comente AGENDA" --out $P
python -m app.services.commercial narrate $P     # só refaz cenas alteradas
python -m app.services.commercial render  $P     # gera $P/out/final.mp4 e final.srt
python -m app.services.commercial verify  $P/out/final.mp4
```

Exemplo pronto (com narração já gerada): `examples/commercials/demo-clinica`.

## O plano (`plan.json`)

Cada cena tem:

| Campo | O que é |
|---|---|
| `narration` | o texto falado na cena |
| `emphasis` | 1–2 trechos da narração que ganham destaque na legenda |
| `component` | o tipo de cena (lista abaixo) |
| `props` | o conteúdo do painel |
| `actions` | o que acontece na tela e em qual palavra: `{"at": "24 horas", "do": "toggle"}` |
| `media` | imagem/vídeo externo (obrigatório no componente `Media`) |

Componentes: `Hook`, `Media`, `PhoneLockScreen`, `WhatsAppChat`, `AgentFlow`, `Calendar`,
`Stopwatch`, `SearchResults`, `Transcription`, `FormCard`, `TicketCards`, `DataTable`,
`MapCard`, `ChecklistStatus`, `BarChart`, `SocialPost`, `DigitalClock`. Os campos de cada
um estão em `app/services/commercial/components.py`; exemplos em `remotion/fixtures/`.

Itens que são alvo de uma ação de revelar (`show`, `typing`, `comment`, `reveal`, `type`)
ficam ocultos até a palavra indicada; os demais aparecem desde o início da cena.

## Efeitos sonoros e trilha

- Trilhas: `resource/songs/` ou envio pela interface.
- Efeitos: sintetizados com FFmpeg em `remotion/public/sfx/`. Para trocar um efeito,
  coloque um arquivo com o mesmo nome em `resource/sfx/` (`whoosh.wav`, `click.wav`,
  `pop.wav`, `notify.wav`, `type.wav`, `impact.wav`, `shimmer.wav`).

## Testes

```bash
uv run python -X utf8 -m pytest -q test/services/test_commercial_*.py
npm --prefix remotion run typecheck
remotion/scripts/stills.sh <Componente> <quadro> [<quadro> ...]   # quadros para revisão visual
```

## Licença do Remotion

Gratuito para pessoas físicas e empresas de até 3 pessoas; acima disso exige licença de
empresa (https://remotion.dev/license).
