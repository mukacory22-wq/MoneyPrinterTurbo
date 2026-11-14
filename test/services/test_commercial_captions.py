import pytest

from app.services.commercial.captions import (
    AlignmentError,
    CaptionGroup,
    align_words,
    find_phrase,
    group_captions,
    normalize_token,
    to_srt,
    tokenize,
)
from app.services.commercial.schema import Word


def W(text, start, end):
    return Word(text=text, start=start, end=end)


def seq(texts, step=0.3, dur=0.25, t0=0.0):
    return [W(t, round(t0 + i * step, 3), round(t0 + i * step + dur, 3)) for i, t in enumerate(texts)]


def test_normalize_token():
    assert normalize_token("Automação,") == "automacao"
    assert normalize_token("R$") == "r"
    assert normalize_token("—") == ""


def test_tokenize_attaches_punctuation_only_tokens():
    assert tokenize("Olha só — veja isso.") == ["Olha", "só —", "veja", "isso."]


def test_align_identical_tokens():
    out = align_words("Você pode vender", seq(["Você", "pode", "vender"]))
    assert [w.text for w in out] == ["Você", "pode", "vender"]
    assert (out[1].start, out[1].end) == (0.3, 0.55)


def test_align_keeps_original_spelling():
    out = align_words("São 11h47, R$ 3.000!", seq(["São", "11h47", "R$", "3.000"]))
    assert [w.text for w in out] == ["São", "11h47", "R$", "3.000"]


def test_align_tts_splits_token():
    out = align_words("atende 24h", seq(["atende", "24", "h"]))
    assert [w.text for w in out] == ["atende", "24h"]
    assert out[1].start == 0.3
    assert out[1].end == 0.85


def test_align_tts_merges_tokens():
    out = align_words("3 mil reais", seq(["3 mil", "reais"]))
    assert [w.text for w in out] == ["3", "mil", "reais"]
    assert out[0].start == 0.0 and out[1].end == 0.25
    assert out[2].start == 0.3


def test_align_raises_on_mismatch():
    with pytest.raises(AlignmentError):
        align_words("Você pode vender automação", seq(["Completamente", "diferente", "disso"]))


def test_align_raises_on_empty_tts():
    with pytest.raises(AlignmentError):
        align_words("Você pode", [])


def test_find_phrase_first_occurrence():
    tokens = tokenize("a agenda e outra agenda aqui")
    assert find_phrase(tokens, "agenda") == (1, 1)


def test_find_phrase_normalized():
    tokens = tokenize("Por 3 mil! Tudo em 41 segundos.")
    assert find_phrase(tokens, "3 MIL") == (1, 2)
    assert find_phrase(tokens, "41 Segundos") == (5, 6)
    assert find_phrase(tokens, "inexistente") is None
    assert find_phrase(tokens, "!!") is None


def test_group_max_words():
    words = seq(["a", "b", "c", "d", "e", "f"])
    groups = group_captions(words, ["a", "b", "c", "d", "e", "f"], max_words=4, max_chars=50)
    assert [[w.text for w in g.words] for g in groups] == [["a", "b", "c", "d"], ["e", "f"]]
    assert groups[0].start == 0.0 and groups[0].end == words[3].end


def test_group_max_chars():
    texts = ["provavelmente", "procuraria", "outro"]
    groups = group_captions(seq(texts), texts, max_words=4, max_chars=18)
    assert [[w.text for w in g.words] for g in groups] == [["provavelmente"], ["procuraria", "outro"]]


def test_group_breaks_on_pause():
    words = [W("um", 0.0, 0.2), W("dois", 0.25, 0.5), W("tres", 0.8, 1.0)]
    groups = group_captions(words, ["um", "dois", "tres"], max_words=4, max_chars=50)
    assert [[w.text for w in g.words] for g in groups] == [["um", "dois"], ["tres"]]


def test_group_breaks_on_sentence_end():
    texts = ["E", "olha", "só", "São"]
    groups = group_captions(seq(texts), ["E", "olha", "só.", "São"], max_words=4, max_chars=50)
    assert [[w.text for w in g.words] for g in groups] == [["E", "olha", "só"], ["São"]]


def test_to_srt_format():
    groups = [CaptionGroup(words=seq(["Você", "pode", "vender"]), start=0.05, end=1.2)]
    assert to_srt(groups) == "1\n00:00:00,050 --> 00:00:01,200\nVocê pode vender\n"
