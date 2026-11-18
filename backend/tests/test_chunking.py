"""Unit tests for chunk_text. Pure function: no mocks needed."""

import re

import pytest

from app.services.chunking import chunk_text


def sentence(n: int, words: int = 12) -> str:
    """A unique, recognisable sentence: 'S7 w w w ... w.'"""
    return f"S{n} " + " ".join(["word"] * words) + "."


def words_of(text: str) -> list[str]:
    return re.findall(r"\S+", text)


# --- Basics ------------------------------------------------------------------------

def test_empty_or_blank_text_gives_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  \t ") == []


def test_short_text_is_one_chunk() -> None:
    assert chunk_text("Refunds take 5 days. Returns take 30 days.") == [
        "Refunds take 5 days. Returns take 30 days."
    ]


def test_whitespace_is_tidied_and_paragraphs_are_kept() -> None:
    text = "First   line\r\ncontinues here.\r\n\r\n\r\nSecond    paragraph."

    assert chunk_text(text) == ["First line continues here.\n\nSecond paragraph."]


# --- Size limits ---------------------------------------------------------------------

def test_no_chunk_is_longer_than_max_chars() -> None:
    text = " ".join(sentence(i) for i in range(60))

    chunks = chunk_text(text, max_chars=300, overlap_chars=60)

    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)


def test_sentences_are_never_cut_in_the_middle_when_they_fit() -> None:
    text = " ".join(sentence(i) for i in range(40))

    for chunk in chunk_text(text, max_chars=300, overlap_chars=60):
        assert chunk.startswith("S") and chunk.endswith(".")


def test_one_huge_sentence_is_split_by_words() -> None:
    text = " ".join(f"w{i}" for i in range(400))  # ~1900 chars, no full stop

    chunks = chunk_text(text, max_chars=200, overlap_chars=0)

    assert all(len(c) <= 200 for c in chunks)
    assert words_of(" ".join(chunks)) == words_of(text)  # nothing lost, nothing doubled


def test_one_giant_word_is_split_by_characters() -> None:
    url = "https://example.com/" + "a" * 450

    chunks = chunk_text(f"See {url} now.", max_chars=200, overlap_chars=0)

    assert all(len(c) <= 200 for c in chunks)
    assert "".join(c.replace(" ", "") for c in chunks) == f"See{url}now."


# --- Overlap ---------------------------------------------------------------------------

def test_next_chunk_starts_with_the_end_of_the_previous_one() -> None:
    text = " ".join(sentence(i) for i in range(30))

    chunks = chunk_text(text, max_chars=300, overlap_chars=100)

    for previous, current in zip(chunks, chunks[1:]):
        last_sentence = previous.split(". ")[-1].strip()
        assert current.startswith(last_sentence.rstrip("."))


def test_zero_overlap_repeats_nothing() -> None:
    text = " ".join(sentence(i) for i in range(30))

    chunks = chunk_text(text, max_chars=300, overlap_chars=0)

    assert words_of(" ".join(chunks)) == words_of(text)


def test_no_text_is_lost_with_overlap() -> None:
    numbers = [p * 10 + i for p in range(8) for i in range(5)]  # 8 paragraphs × 5 sentences
    text = "\n\n".join(
        " ".join(sentence(p * 10 + i) for i in range(5)) for p in range(8)
    )

    chunks = chunk_text(text, max_chars=400, overlap_chars=120)

    joined = " ".join(chunks)
    for n in numbers:
        assert f"S{n} " in joined


def test_overlap_is_skipped_when_it_would_not_leave_room() -> None:
    long_sentence = "L " + " ".join(["x"] * 60) + "."  # ~123 chars
    text = f"{long_sentence} {long_sentence} {long_sentence}"

    chunks = chunk_text(text, max_chars=130, overlap_chars=129)

    assert all(len(c) <= 130 for c in chunks)
    assert len(chunks) == 3


# --- Config validation ------------------------------------------------------------------

@pytest.mark.parametrize(("max_chars", "overlap"), [(50, 0), (500, 500), (500, -1)])
def test_invalid_settings_are_rejected(max_chars: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_text("Some text.", max_chars=max_chars, overlap_chars=overlap)
