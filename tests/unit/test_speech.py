import io
import wave

import pytest

from qualifai.llm.speech import join_wav, split_for_speech

pytestmark = pytest.mark.unit


def _wav(frames: bytes) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(frames)
    return out.getvalue()


def test_short_text_is_one_piece_and_whitespace_is_tidied():
    assert split_for_speech("  Hello   there.\nHow are you? ", 200) == ["Hello there. How are you?"]
    assert split_for_speech("Any length at all. " * 40, None) == [
        ("Any length at all. " * 40).strip()
    ]
    assert split_for_speech("   ", 200) == []


def test_long_text_is_cut_at_sentence_ends_and_packed_under_the_limit():
    text = "I'm Arjun, your interviewer. We have about 45 minutes. Please introduce yourself. " * 4
    pieces = split_for_speech(text, 100)

    assert all(len(p) <= 100 for p in pieces) and len(pieces) > 1
    assert " ".join(pieces) == " ".join(text.split())  # nothing lost, nothing reordered
    assert all(p.endswith(".") for p in pieces)  # never cut inside a sentence here
    assert any(p.count(".") > 1 for p in pieces)  # short sentences share a piece


def test_a_sentence_longer_than_the_limit_is_cut_at_spaces():
    pieces = split_for_speech("word " * 60, 50)
    assert all(len(p) <= 50 for p in pieces) and " ".join(pieces) == ("word " * 60).strip()


def test_wav_pieces_are_joined_into_one_file_in_order():
    joined = join_wav([_wav(b"\x01\x00" * 10), _wav(b"\x02\x00" * 5)])
    with wave.open(io.BytesIO(joined), "rb") as w:
        assert (w.getnchannels(), w.getframerate(), w.getnframes()) == (1, 24000, 15)
        assert w.readframes(15) == b"\x01\x00" * 10 + b"\x02\x00" * 5
    assert join_wav([b"as-is"]) == b"as-is"
