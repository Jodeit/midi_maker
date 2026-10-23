# MIDI Maker

Paste a YouTube piano link, get a MIDI file with the **right hand** and **left hand** on separate tracks (split at middle C), plus an in-browser preview.

Pipeline: `yt-dlp` → [Demucs](https://github.com/facebookresearch/demucs) (removes vocals/drums) → [Transkun](https://github.com/Yujia-Yan/Transkun) (piano transcription) → split by pitch.

The page (`docs/`) is static and hosted on GitHub Pages. The heavy work runs in a small Python server on your own machine, reached through a free Cloudflare tunnel so an iPad can use it.

## Setup (once, on your Mac)

```bash
brew install ffmpeg cloudflared uv
uv venv -p 3.12 .venv
uv pip install -p .venv/bin/python -r requirements.txt
```

## Use

```bash
./run.sh
```

It prints a link. Open it on your iPad (or anywhere); it fills in the backend address and access key, then paste a YouTube link and tap **Make MIDI**. Expect a few minutes per song on CPU; the first run also downloads the Demucs model.

Keep the Mac awake and `run.sh` running while you use it. The tunnel address changes each run, so use the fresh link each time.

## GitHub Pages

Settings → Pages → Deploy from branch → `main` / `docs`.

## Notes

- Everything except vocals and drums is transcribed, so a sung section may add a few stray notes.
- Only download audio you have the right to use; this is meant for personal transcription practice.
