"""Chunking: split a long text into overlapping pieces small enough to embed and retrieve.

Why chunks?
- An embedding of a whole 20-page PDF is a blurry "average"; a paragraph-sized chunk is precise.
- RAG sends only the few best chunks to the LLM, not whole documents (fewer tokens).

How this splitter works:
1. Break the text into sentences, remembering where paragraphs start.
2. Pack whole sentences into a chunk until adding one more would exceed `max_chars`.
3. Start the next chunk with the last sentence(s) of the previous one (the OVERLAP),
   so a fact that sits on a chunk border is still complete in at least one chunk.
Sentences longer than `max_chars` are split by words (and very long "words" by characters).

Sizes are in characters, not tokens: ~4 characters ≈ 1 token for English text.
"""

import re
from dataclasses import dataclass

# Tested on the sample handbook: 500-char chunks ranked the right chunk #1 (0.778) where
# 1000-char chunks, mixing several topics, ranked it #4 (0.571). Re-check in RAG evaluation.
DEFAULT_MAX_CHARS = 500  # ≈ 125 tokens
DEFAULT_OVERLAP_CHARS = 100  # ≈ 25 tokens

PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
# Split after . ! or ? followed by whitespace. Simple on purpose: abbreviations such as
# "e.g. this" may be split too, which only costs a slightly earlier chunk border.
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class _Piece:
    text: str
    starts_paragraph: bool


def chunk_text(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[str]:
    """Split `text` into chunks of at most `max_chars` characters with sentence overlap."""
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100.")
    if not 0 <= overlap_chars < max_chars:
        raise ValueError("overlap_chars must be between 0 and max_chars - 1.")

    pieces = _split_into_pieces(text, max_chars)
    if not pieces:
        return []

    chunks: list[str] = []
    current: list[_Piece] = []

    for piece in pieces:
        if current and _length(current + [piece]) > max_chars:
            chunks.append(_join(current))
            current = _overlap_tail(current, overlap_chars)
            # The overlap must never stop the new piece from fitting.
            while current and _length(current + [piece]) > max_chars:
                current.pop(0)
        current.append(piece)

    if current:
        chunks.append(_join(current))
    return chunks


# --- Helpers -------------------------------------------------------------------------

def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in text.split("\n")]  # tidy spaces inside lines
    return "\n".join(lines).strip()


def _split_into_pieces(text: str, max_chars: int) -> list[_Piece]:
    pieces: list[_Piece] = []
    for paragraph in PARAGRAPH_BREAK.split(_normalize(text)):
        paragraph = " ".join(paragraph.split())  # single line breaks inside a paragraph → spaces
        if not paragraph:
            continue
        first = True
        for sentence in SENTENCE_END.split(paragraph):
            for part in _split_long(sentence, max_chars):
                pieces.append(_Piece(part, starts_paragraph=first))
                first = False
    return pieces


def _split_long(sentence: str, max_chars: int) -> list[str]:
    """A sentence that alone is too long is split by words; a huge 'word' by characters."""
    if len(sentence) <= max_chars:
        return [sentence]
    parts: list[str] = []
    current = ""
    for word in sentence.split(" "):
        while len(word) > max_chars:  # e.g. a very long URL
            if current:
                parts.append(current)
                current = ""
            parts.append(word[:max_chars])
            word = word[max_chars:]
        candidate = f"{current} {word}" if current else word
        if len(candidate) > max_chars:
            parts.append(current)
            current = word
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def _join(pieces: list[_Piece]) -> str:
    out = ""
    for index, piece in enumerate(pieces):
        if index == 0:
            out = piece.text
        else:
            out += ("\n\n" if piece.starts_paragraph else " ") + piece.text
    return out


def _length(pieces: list[_Piece]) -> int:
    return len(_join(pieces))


def _overlap_tail(pieces: list[_Piece], overlap_chars: int) -> list[_Piece]:
    """The last sentences of a chunk whose total length fits in `overlap_chars`."""
    tail: list[_Piece] = []
    for piece in reversed(pieces):
        if _length([piece] + tail) > overlap_chars:
            break
        tail.insert(0, piece)
    if tail:
        # The repeated text starts the new chunk, so it begins a "paragraph" there.
        tail[0] = _Piece(tail[0].text, starts_paragraph=True)
    return tail
