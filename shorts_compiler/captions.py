"""Transcribe a clip with faster-whisper and build an ASS caption file.

Words are grouped into short chunks and the active chunk is shown large,
bold and centered low, which is the usual retention-friendly caption style.
"""
from pathlib import Path

WORDS_PER_CHUNK = 3


def transcribe(path: Path, model_size: str = "base") -> list[dict]:
    """Return [{'start', 'end', 'word'}] for every spoken word."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, compute_type="int8")
    segments, _ = model.transcribe(str(path), word_timestamps=True, vad_filter=True)
    return [
        {"start": w.start, "end": w.end, "word": w.word.strip()}
        for seg in segments
        for w in (seg.words or [])
    ]


def _ts(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def write_ass(words: list[dict], out: Path, width: int, height: int) -> bool:
    """Write captions to `out`. Returns False if there was nothing to caption."""
    if not words:
        return False
    size = int(height * (0.055 if height > width else 0.075))
    margin_v = int(height * (0.22 if height > width else 0.10))
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {width}\nPlayResY: {height}\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BackColour,Bold,"
        "BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV\n"
        f"Style: Default,Arial,{size},&H00FFFFFF,&H00000000,&H80000000,-1,1,"
        f"{max(4, size // 9)},2,2,60,60,{margin_v}\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Text\n"
    )
    lines = []
    for i in range(0, len(words), WORDS_PER_CHUNK):
        chunk = words[i:i + WORDS_PER_CHUNK]
        end = chunk[-1]["end"]
        if i + WORDS_PER_CHUNK < len(words):  # hold until the next chunk starts
            end = max(end, words[i + WORDS_PER_CHUNK]["start"])
        text = " ".join(w["word"] for w in chunk).upper()
        lines.append(f"Dialogue: 0,{_ts(chunk[0]['start'])},{_ts(end)},Default,{text}")
    out.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return True
