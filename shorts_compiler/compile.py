#!/usr/bin/env python3
"""Compile a folder of short clips into one punchy video.

    python compile.py clips/ -o out/compilation.mp4 --captions --music bed.mp3

Each clip is normalized (size, fps, audio), optionally captioned, then all
clips are joined with hard cuts and an optional ducked music bed is mixed in.
"""
import argparse
import tempfile
from pathlib import Path

import captions
from ffutil import duration, has_audio, run

EXTS = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}
FPS = 30


def layout(vertical: bool) -> tuple[int, int]:
    return (1080, 1920) if vertical else (1920, 1080)


def normalize(src: Path, dst: Path, w: int, h: int, vertical: bool,
              ass: Path | None, max_seconds: float | None) -> None:
    """Re-encode one clip to the common format shared by every clip."""
    if vertical:
        vf = f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    else:
        # Blurred, zoomed copy of the clip fills the frame behind the original.
        vf = (
            f"[0:v]split[a][b];"
            f"[a]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=30:5[bg];"
            f"[b]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
    vf += f",fps={FPS},setsar=1,format=yuv420p"
    if ass:
        vf += f",subtitles='{ass.as_posix()}'"
    vf += "[v]"

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src)]
    if has_audio(src):
        af = "[0:a]aresample=48000,aformat=channel_layouts=stereo[a]"
    else:
        cmd += ["-f", "lavfi", "-t", f"{duration(src):.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        af = "[1:a]anull[a]"
    cmd += ["-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]"]
    cmd += ["-shortest"]
    if max_seconds:
        cmd += ["-t", str(max_seconds)]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(dst)]
    run(cmd)


def join(parts: list[Path], dst: Path, music: Path | None, music_volume: float) -> None:
    """Concatenate the normalized clips and optionally mix in ducked music."""
    listing = dst.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in parts))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing)]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music), "-filter_complex",
                f"[1:a]volume={music_volume}[m];[0:a]asplit[v1][v2];"
                f"[m][v1]sidechaincompress=threshold=0.04:ratio=8:attack=20:release=400[duck];"
                f"[v2][duck]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy"]
    else:
        cmd += ["-c:v", "copy", "-c:a", "copy"]
    cmd += ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)] if music \
        else ["-movflags", "+faststart", str(dst)]
    run(cmd)
    listing.unlink()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("clips_dir", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("out/compilation.mp4"))
    p.add_argument("--vertical", action="store_true", help="9:16 output (upload as a Short, <3 min)")
    p.add_argument("--hook", type=str, help="filename of the clip to play first")
    p.add_argument("--max-clip-seconds", type=float, help="trim every clip to this length")
    p.add_argument("--captions", action="store_true", help="burn in animated captions (Whisper)")
    p.add_argument("--whisper-model", default="base")
    p.add_argument("--music", type=Path, help="background music, ducked under speech")
    p.add_argument("--music-volume", type=float, default=0.3)
    p.add_argument("--transcript-out", type=Path, help="write all transcripts here (feeds metadata.py)")
    args = p.parse_args()

    clips = sorted(f for f in args.clips_dir.iterdir() if f.suffix.lower() in EXTS)
    if not clips:
        p.error(f"no video files found in {args.clips_dir}")
    if args.hook:
        hook = [c for c in clips if c.name == args.hook]
        if not hook:
            p.error(f"--hook {args.hook} not found in {args.clips_dir}")
        clips = hook + [c for c in clips if c != hook[0]]

    w, h = layout(args.vertical)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    transcripts = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        parts = []
        for i, clip in enumerate(clips, 1):
            print(f"[{i}/{len(clips)}] {clip.name}")
            ass = None
            if args.captions:
                words = captions.transcribe(clip, args.whisper_model)
                transcripts.append(f"## {clip.name}\n" + " ".join(x["word"] for x in words))
                ass = tmp / f"{i:03d}.ass"
                if not captions.write_ass(words, ass, w, h):
                    ass = None
            out = tmp / f"{i:03d}.mp4"
            normalize(clip, out, w, h, args.vertical, ass, args.max_clip_seconds)
            parts.append(out)
        join(parts, args.output, args.music, args.music_volume)

    if args.transcript_out:
        args.transcript_out.write_text("\n\n".join(transcripts), encoding="utf-8")
    print(f"Done: {args.output} ({duration(args.output):.1f}s)")


if __name__ == "__main__":
    main()
