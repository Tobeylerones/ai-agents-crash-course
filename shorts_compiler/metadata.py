#!/usr/bin/env python3
"""Draft YouTube titles, a description and tags from the clip transcripts.

    python metadata.py transcripts.txt -o out/metadata.json

Needs ANTHROPIC_API_KEY. Review the output before uploading.
"""
import argparse
import json
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-5-5"

PROMPT = """These are transcripts of short clips compiled into one YouTube video.

{transcripts}

Return only JSON with keys:
  "titles": 5 title options, under 70 characters, curiosity-driven but not misleading
  "description": 2-3 short paragraphs, first line must work as a hook
  "tags": up to 15 tags
  "hook_clip": filename of the clip that should open the video"""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("transcripts", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("out/metadata.json"))
    args = p.parse_args()

    msg = anthropic.Anthropic().messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": PROMPT.format(transcripts=args.transcripts.read_text())}],
    )
    text = msg.content[0].text.strip()
    text = text.removeprefix("```json").removesuffix("```").strip()
    data = json.loads(text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2))
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
