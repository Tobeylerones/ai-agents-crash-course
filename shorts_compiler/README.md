# shorts_compiler

Turn a folder of short clips into one video, and optionally upload it to YouTube.

```bash
sudo apt install ffmpeg
pip install -r requirements.txt

# 1. Compile (16:9 with blurred backdrop by default; --vertical for 9:16)
python compile.py clips/ -o out/compilation.mp4 --captions --music bed.mp3 \
    --transcript-out out/transcripts.txt

# 2. Draft titles/description/tags (needs ANTHROPIC_API_KEY)
python metadata.py out/transcripts.txt -o out/metadata.json

# 3. Upload as private, then review in YouTube Studio
python upload.py out/compilation.mp4 --metadata out/metadata.json
```

Useful flags on `compile.py`: `--hook clip.mp4` (play this clip first),
`--max-clip-seconds 8`, `--whisper-model small`.

Tips: open with your strongest clip, keep clips under ~8s, and make the
thumbnail separately. `upload.py` needs `client_secret.json` (see its docstring);
`client_secret.json` and `token.json` are git-ignored.
