"""Alinhamento dos tempos de palavra do TTS ao roteiro e montagem das legendas."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.services.commercial.schema import Word

_EDGE_PUNCT = " .,!?;:…—–-\"“”‘’'()[]"
_SENTENCE_END = (".", "!", "?", "…", ":", ";")
MIN_ALIGNMENT_RATIO = 0.9


class AlignmentError(ValueError):
    """Os tempos do TTS não correspondem ao texto da narração."""


def normalize_token(text: str) -> str:
    flat = unicodedata.normalize("NFKD", text.lower())
    flat = "".join(ch for ch in flat if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", flat)


def tokenize(text: str) -> list[str]:
    """Divide por espaços; tokens só de pontuação são anexados ao anterior."""
    tokens: list[str] = []
    for raw in text.split():
        if normalize_token(raw) or not tokens:
            tokens.append(raw)
        else:
            tokens[-1] = f"{tokens[-1]} {raw}"
    return tokens


def _display(token: str) -> str:
    return token.strip(_EDGE_PUNCT) or token


def find_phrase(tokens: list[str], phrase: str) -> tuple[int, int] | None:
    """Índices (primeiro, último) da 1ª ocorrência normalizada de ``phrase``."""
    target = [n for n in (normalize_token(p) for p in phrase.split()) if n]
    if not target:
        return None
    norm = [normalize_token(t) for t in tokens]
    for i in range(len(norm) - len(target) + 1):
        if norm[i : i + len(target)] == target:
            return i, i + len(target) - 1
    return None


def align_words(narration: str, tts_words: list[Word]) -> list[Word]:
    """Devolve um ``Word`` por token da narração, com a grafia do roteiro.

    Compara, caractere a caractere, o texto normalizado da narração com o das
    palavras devolvidas pelo TTS. O tempo de cada token vem dos caracteres do
    TTS a que ele corresponde (interpolando dentro da palavra do TTS quando ela
    cobre mais de um token).
    """
    tokens = [t for t in tokenize(narration) if normalize_token(t)]
    if not tokens:
        raise AlignmentError("narração sem palavras")

    a_text = "".join(normalize_token(t) for t in tokens)
    # Para cada caractere do TTS: (tempo de início, tempo de fim) interpolados.
    b_chars: list[str] = []
    b_times: list[tuple[float, float]] = []
    for word in tts_words:
        norm = normalize_token(word.text)
        span = max(word.end - word.start, 0.0)
        for k, ch in enumerate(norm):
            b_chars.append(ch)
            b_times.append(
                (word.start + span * k / len(norm), word.start + span * (k + 1) / len(norm))
            )
    b_text = "".join(b_chars)
    if not b_text:
        raise AlignmentError("o serviço de voz não devolveu tempos de palavra")

    matcher = SequenceMatcher(None, a_text, b_text, autojunk=False)
    if matcher.ratio() < MIN_ALIGNMENT_RATIO:
        tag, i1, i2, j1, j2 = next(
            (op for op in matcher.get_opcodes() if op[0] != "equal"), ("replace", 0, 0, 0, 0)
        )
        raise AlignmentError(
            "tempos de palavra não batem com a narração: "
            f"roteiro '{a_text[max(i1 - 8, 0) : i2 + 8]}' x voz '{b_text[max(j1 - 8, 0) : j2 + 8]}'"
        )

    a_to_b: dict[int, int] = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            a_to_b[block.a + offset] = block.b + offset

    aligned: list[Word] = []
    cursor = 0
    for token in tokens:
        size = len(normalize_token(token))
        mapped = [a_to_b[i] for i in range(cursor, cursor + size) if i in a_to_b]
        cursor += size
        if mapped:
            start, end = b_times[mapped[0]][0], b_times[mapped[-1]][1]
        elif aligned:
            start = end = aligned[-1].end
        else:
            raise AlignmentError(f"sem tempo para a primeira palavra '{token}'")
        aligned.append(Word(text=_display(token), start=round(start, 3), end=round(end, 3)))
    return aligned


@dataclass
class CaptionGroup:
    words: list[Word]
    start: float
    end: float


def group_captions(
    words: list[Word],
    raw_tokens: list[str],
    max_words: int = 4,
    max_chars: int = 18,
    pause: float = 0.25,
) -> list[CaptionGroup]:
    """Agrupa palavras em blocos curtos; ``raw_tokens`` traz a pontuação."""
    groups: list[list[Word]] = []
    current: list[Word] = []
    for index, word in enumerate(words):
        if current:
            previous = words[index - 1]
            prev_raw = raw_tokens[index - 1].rstrip() if index - 1 < len(raw_tokens) else ""
            chars = sum(len(w.text) for w in current) + len(current) + len(word.text)
            if (
                len(current) >= max_words
                or chars > max_chars
                or word.start - previous.end > pause
                or prev_raw.rstrip("\"”’')").endswith(_SENTENCE_END)
            ):
                groups.append(current)
                current = []
        current.append(word)
    if current:
        groups.append(current)
    return [CaptionGroup(words=g, start=g[0].start, end=g[-1].end) for g in groups]


def _srt_time(seconds: float) -> str:
    millis = max(int(round(seconds * 1000)), 0)
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def to_srt(groups: list[CaptionGroup]) -> str:
    blocks = [
        f"{i}\n{_srt_time(g.start)} --> {_srt_time(g.end)}\n{' '.join(w.text for w in g.words)}\n"
        for i, g in enumerate(groups, start=1)
    ]
    return "\n".join(blocks)
