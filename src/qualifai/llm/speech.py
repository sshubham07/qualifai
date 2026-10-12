"""Helpers for the speech task (ADR-0024): hosted speech models take a short text per request and
answer with a WAV file, so a question is cut into sentence-sized pieces and the audio joined."""

from __future__ import annotations

import io
import re
import wave
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass

MEDIA_TYPES = {"wav": "audio/wav", "mp3": "audio/mpeg"}


@dataclass(frozen=True, slots=True)
class Speech:
    """Audio as it is produced, so playing can start before the model has finished."""

    media_type: str
    chunks: AsyncIterator[bytes]


async def chunks_of(
    *parts: bytes, then: AsyncIterator[bytes] | None = None
) -> AsyncIterator[bytes]:
    for part in parts:
        yield part
    if then is not None:
        async for part in then:
            yield part


_SENTENCE_END = re.compile(r"(?<=[.!?;:])\s+")


def split_for_speech(text: str, limit: int | None) -> list[str]:
    """Pieces of at most `limit` characters, cut at sentence ends where possible, then at
    spaces. Sentences are packed together so the voice keeps its flow."""
    text = " ".join(text.split())
    if not text:
        return []
    if limit is None or len(text) <= limit:
        return [text]
    words: list[str] = []
    for sentence in _SENTENCE_END.split(text):
        words.append(sentence) if len(sentence) <= limit else words.extend(sentence.split(" "))
    pieces: list[str] = []
    for part in words:
        part = part[:limit]  # a single "word" longer than the limit; never the case for speech
        if pieces and len(pieces[-1]) + 1 + len(part) <= limit:
            pieces[-1] = f"{pieces[-1]} {part}"
        else:
            pieces.append(part)
    return pieces


def join_wav(parts: Sequence[bytes]) -> bytes:
    """One WAV from several with the same format (same model and voice)."""
    if len(parts) == 1:
        return parts[0]
    out = io.BytesIO()
    with wave.open(out, "wb") as joined:
        for i, part in enumerate(parts):
            with wave.open(io.BytesIO(part), "rb") as piece:
                if i == 0:
                    joined.setparams(piece.getparams())
                joined.writeframes(piece.readframes(piece.getnframes()))
    return out.getvalue()
