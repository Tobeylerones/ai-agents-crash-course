"""Thin helpers around the ffmpeg / ffprobe binaries."""
import json
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])}... failed:\n{proc.stderr[-2000:]}")


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def duration(path: Path) -> float:
    return float(probe(path)["format"]["duration"])


def has_audio(path: Path) -> bool:
    return any(s["codec_type"] == "audio" for s in probe(path)["streams"])
