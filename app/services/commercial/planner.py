"""Roteiro e planejamento visual por IA: briefing → Plan validado."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from pydantic import ValidationError

from app.services.commercial.components import ACTIONS, PROPS_MODELS
from app.services.commercial.schema import Brief, MusicSettings, Plan, Status, validate_plan

PROMPT_FILE = Path(__file__).parent / "prompts" / "planner.md"
# Medido na narração real (Edge TTS, Antonio, +8%), já contando as pausas entre cenas.
WORDS_PER_SECOND = 2.2
DEFAULT_MUSIC = "resource/songs/output003.mp3"
# Componentes que a IA pode usar: os já implementados no Remotion, exceto "Media"
# (que depende de arquivos enviados pelo usuário). Um teste garante que cada um
# tem implementação/fixture em remotion/.
PLANNABLE = [name for name in PROPS_MODELS if name != "Media"]

DESCRIPTIONS: dict[str, str] = {
    "Hook": "Frase de impacto gigante no centro (gancho ou CTA). Palavras em MAIÚSCULAS ganham destaque.",
    "PhoneLockScreen": "Celular na tela de bloqueio: hora, data, alarme opcional e notificações que chegam.",
    "WhatsAppChat": "Conversa de WhatsApp no celular: mensagens de texto e de áudio, digitando, gravando.",
    "AgentFlow": "Painel do fluxo de um agente/automação: etapas com ícones, interruptor liga/desliga, mostrador e contador.",
    "Calendar": "Agenda de um dia: compromissos ocupados, horários livres que aparecem e opções sugeridas.",
    "Stopwatch": "Cronômetro com etapas marcadas no tempo (prova de velocidade).",
    "SearchResults": "Busca sendo digitada e lista de resultados (ex.: concorrentes no mapa).",
    "Transcription": "Áudio sendo transcrito: onda sonora tocando e o texto aparecendo.",
    "FormCard": "Ficha em papel com campos manuscritos e opções marcáveis (triagem, cadastro).",
    "TicketCards": "Cartões de opção (horários, planos) com escolha e carimbo de confirmação.",
    "DataTable": "Planilha/tabela com uma nova linha sendo registrada.",
    "MapCard": "Mapa com rota até um local e botão de enviar localização.",
    "ChecklistStatus": "Lista de itens cujo status muda de pendente para concluído.",
    "BarChart": "Gráfico de barras que cresce, com uma barra em destaque (resultado).",
    "SocialPost": "Post de rede social com etapas e comentários chegando com a palavra-chave do CTA.",
    "DigitalClock": "Relógio despertador digital mostrando a hora (clima de madrugada/manhã).",
}

Generate = Callable[[str], str]


class PlannerError(RuntimeError):
    """A IA não devolveu um plano válido."""


def _catalog() -> str:
    blocks = []
    for name in PLANNABLE:
        schema = json.dumps(PROPS_MODELS[name].model_json_schema(), ensure_ascii=False)
        actions = ", ".join(sorted(ACTIONS[name])) or "nenhuma"
        blocks.append(
            f"### {name}\n{DESCRIPTIONS[name]}\nAções permitidas: {actions}\nProps (JSON Schema): {schema}"
        )
    return "\n\n".join(blocks)


def build_planner_prompt(brief: Brief, errors: list[str] | None = None) -> str:
    budget = round(brief.target_seconds * WORDS_PER_SECOND)
    retry = ""
    if errors:
        retry = (
            "\n## Sua resposta anterior foi rejeitada\nCorrija estes erros e devolva o JSON completo de novo:\n"
            + "\n".join(f"- {e}" for e in errors[:30])
        )
    return PROMPT_FILE.read_text(encoding="utf-8").format(
        target_seconds=brief.target_seconds,
        topic=brief.topic,
        audience=brief.audience,
        tone=brief.tone or "direto e confiante",
        cta=brief.cta or "convide a pessoa a comentar ou chamar no direct",
        word_budget=budget,
        word_min=round(budget * 0.9),
        word_max=round(budget * 1.1),
        catalog=_catalog(),
        retry=retry,
    )


def _extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("a resposta não contém um objeto JSON")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
        raise ValueError('o JSON precisa ter a lista "scenes"')
    return data


def parse_plan_response(text: str, brief: Brief, plan_id: str) -> tuple[Plan | None, list[str]]:
    """Converte a resposta da IA em Plan. Devolve (plano, erros)."""
    try:
        data = _extract_json(text)
    except ValueError as exc:  # inclui json.JSONDecodeError
        return None, [f"JSON inválido: {exc}"]
    scenes = [
        {k: v for k, v in scene.items() if k != "audio"} if isinstance(scene, dict) else scene
        for scene in data["scenes"]
    ]
    try:
        plan = Plan(
            id=plan_id,
            brief=brief,
            music=MusicSettings(file=DEFAULT_MUSIC),
            scenes=scenes,
            status=Status(plan="done"),
        )
    except ValidationError as exc:
        return None, [
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        ]
    errors = validate_plan(plan)
    return (None, errors) if errors else (plan, [])


def _default_generate(prompt: str) -> str:
    from app.services import llm  # import tardio: carrega a configuração do app

    return llm._generate_response(prompt)


def generate_plan(brief: Brief, plan_id: str, generate: Generate | None = None) -> Plan:
    """Pede o plano à IA; em caso de erro de validação, tenta mais uma vez."""
    generate = generate or _default_generate
    errors: list[str] | None = None
    for _ in range(2):
        response = generate(build_planner_prompt(brief, errors))
        if isinstance(response, str) and response.strip().startswith("Error:"):
            raise PlannerError(f"o serviço de IA falhou: {response.strip()}")
        plan, errors = parse_plan_response(response, brief, plan_id)
        if plan is not None:
            return plan
    raise PlannerError("a IA não devolveu um plano válido:\n" + "\n".join(errors or []))
