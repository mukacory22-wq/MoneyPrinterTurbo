"""Catálogo de componentes visuais: modelos de props e ações permitidas.

Os modelos aqui são a fonte da verdade do conteúdo de cada cena. O lado
Remotion espelha estes campos com zod; ``test_python_and_zod_agree`` garante a
paridade.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AppIcon = Literal[
    "whatsapp", "calendar", "pix", "alarm", "ai", "mic", "maps", "sheets",
    "instagram", "bell", "generic",
]
ComponentName = Literal[
    "Hook", "Media", "PhoneLockScreen", "WhatsAppChat", "AgentFlow", "Calendar",
    "Stopwatch", "SearchResults", "Transcription", "FormCard", "TicketCards",
    "DataTable", "MapCard", "ChecklistStatus", "BarChart", "SocialPost",
    "DigitalClock",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Item(_Strict):
    id: str = Field(min_length=1)


class LabelValue(_Strict):
    label: str
    value: str


# --- Props por componente -------------------------------------------------

class HookProps(_Strict):
    text: str


class MediaProps(_Strict):
    fit: Literal["panel", "fullscreen"] = "panel"


class Alarm(_Item):
    label: str
    sub: str = ""


class Notification(_Item):
    app: AppIcon
    title: str
    body: str
    meta: str = ""


class PhoneLockScreenProps(_Strict):
    time: str
    date: str
    alarm: Alarm | None = None
    notifications: list[Notification] = []


class Contact(_Strict):
    name: str
    subtitle: str = ""


class ChatMessage(_Item):
    sender: Literal["them", "me"]
    kind: Literal["text", "audio"] = "text"
    text: str = ""
    audio_seconds: int = 0
    time: str = ""


class WhatsAppChatProps(_Strict):
    contact: Contact
    messages: list[ChatMessage]
    composer: Literal["idle", "recording"] = "idle"


class FlowStep(_Item):
    icon: AppIcon
    title: str
    subtitle: str = ""


class Counter(_Strict):
    label: str
    start: int
    end: int


class AgentFlowProps(_Strict):
    title: str
    toggle_off: str
    toggle_on: str
    steps: list[FlowStep]
    dial_label: str = "24h"
    counter: Counter


class CalendarEvent(_Item):
    title: str
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")
    kind: Literal["busy", "free", "break"] = "busy"


class Option(_Item):
    label: str


class CalendarSide(_Strict):
    title: str
    subtitle: str = ""
    options: list[Option] = []


class CalendarProps(_Strict):
    title: str
    date: str
    hours: tuple[int, int]
    events: list[CalendarEvent]
    side: CalendarSide


class TimedStep(_Item):
    at_seconds: int
    label: str


class StopwatchProps(_Strict):
    total_seconds: int
    steps: list[TimedStep]


class SearchResult(_Item):
    name: str
    meta: str = ""
    status: str = ""
    tone: Literal["bad", "good", "neutral"] = "neutral"
    button: str = ""


class SearchResultsProps(_Strict):
    query: str
    results: list[SearchResult]


class TranscriptionProps(_Strict):
    title: str
    sender: str
    duration_seconds: int
    text: str
    highlight: str = ""


class FormOption(_Item):
    title: str
    subtitle: str = ""


class FormCardProps(_Strict):
    title: str
    subtitle: str = ""
    fields: list[LabelValue]
    section: str = ""
    options: list[FormOption]


class Ticket(_Item):
    label: str
    value: str


class TicketCardsProps(_Strict):
    title: str
    subtitle: str = ""
    fields: list[LabelValue]
    cards: list[Ticket]
    chosen_label: str = ""
    stamp_text: str = "CONFIRMADA"


class TableRow(_Item):
    cells: list[str]


class DataTableProps(_Strict):
    title: str
    columns: list[str]
    rows: list[TableRow]


class Place(_Strict):
    name: str
    address: str


class MapCardProps(_Strict):
    place: Place
    button: str = "Enviar"
    sent_label: str


class ChecklistItem(_Item):
    time: str
    name: str
    pending_label: str
    done_label: str


class ChecklistStatusProps(_Strict):
    title: str
    header_left: str = ""
    header_right: str = ""
    items: list[ChecklistItem]


class Bar(_Item):
    label: str
    value: float


class BarChartProps(_Strict):
    title: str
    badge: str = ""
    bars: list[Bar]


class SocialStep(_Item):
    icon: AppIcon
    label: str


class SocialComment(_Item):
    user: str
    keyword: str


class SocialPostProps(_Strict):
    account: Contact
    title: str
    steps: list[SocialStep]
    comments: list[SocialComment]
    count_label: str = ""


class DigitalClockProps(_Strict):
    time_from: str
    time_to: str | None = None
    footer_left: str = ""
    footer_right: str = ""


PROPS_MODELS: dict[str, type[BaseModel]] = {
    "Hook": HookProps,
    "Media": MediaProps,
    "PhoneLockScreen": PhoneLockScreenProps,
    "WhatsAppChat": WhatsAppChatProps,
    "AgentFlow": AgentFlowProps,
    "Calendar": CalendarProps,
    "Stopwatch": StopwatchProps,
    "SearchResults": SearchResultsProps,
    "Transcription": TranscriptionProps,
    "FormCard": FormCardProps,
    "TicketCards": TicketCardsProps,
    "DataTable": DataTableProps,
    "MapCard": MapCardProps,
    "ChecklistStatus": ChecklistStatusProps,
    "BarChart": BarChartProps,
    "SocialPost": SocialPostProps,
    "DigitalClock": DigitalClockProps,
}

ACTIONS: dict[str, set[str]] = {
    "Hook": set(),
    "Media": set(),
    "PhoneLockScreen": {"show", "press"},
    "WhatsAppChat": {"show", "typing", "play"},
    "AgentFlow": {"activate", "toggle", "count"},
    "Calendar": {"scan", "show"},
    "Stopwatch": {"mark"},
    "SearchResults": {"type", "highlight"},
    "Transcription": {"play", "highlight"},
    "FormCard": {"write", "check"},
    "TicketCards": {"choose", "stamp"},
    "DataTable": {"type"},
    "MapCard": {"route", "send"},
    "ChecklistStatus": {"done"},
    "BarChart": {"grow", "highlight"},
    "SocialPost": {"reveal", "comment"},
    "DigitalClock": {"set"},
}

# Ações que revelam um alvo: o alvo fica oculto até a ação acontecer.
REVEAL_ACTIONS = {"show", "typing", "comment", "reveal", "type"}


def target_ids(component: str, props: dict) -> set[str]:
    """Coleta todos os ``id`` de itens aninhados nos props (alvos de ação)."""
    found: set[str] = set()

    def walk(value):
        if isinstance(value, dict):
            item_id = value.get("id")
            if isinstance(item_id, str):
                found.add(item_id)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(props)
    return found
