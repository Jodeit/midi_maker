---
title: MIDI Maker
emoji: 🎹
colorFrom: blue
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# MIDI Maker

Paste a YouTube or Instagram piano link, get a MIDI file with the **right hand** and **left hand** on separate tracks (split at middle C), plus an in-browser preview.

Pipeline: `yt-dlp` → [Demucs](https://github.com/facebookresearch/demucs) (removes vocals/drums) → [Transkun](https://github.com/Yujia-Yan/Transkun) V2 Aug (piano transcription; its weights download automatically on first use) → split by pitch.

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

## Same-Wi-Fi mode (no tunnel)

If a tunnel can't connect (e.g. a corporate security client blocks it), serve everything from the Mac and open it from an iPad on the same Wi-Fi:

```bash
./run.sh lan
```

Open the printed `http://<your-mac>.local:8000/?key=...` link on the iPad. macOS may ask to allow incoming connections for Python; allow it.

## Hosted on Hugging Face (works from an iPad with your Mac off)

1. Create a free account at huggingface.co, then **New Space** → SDK **Docker** (blank), CPU basic (free). Name it e.g. `midi-maker`.
2. In the Space **Settings → Variables and secrets**, add a secret `MIDI_MAKER_KEY` (any long random string). This is your access key.
3. Push this repo to the Space (use a HF access token with write permission as the password):

```bash
git remote add space https://huggingface.co/spaces/<your-username>/midi-maker
git push space main
```

4. Wait for the build (about 10 minutes the first time). Then open `https://<your-username>-midi-maker.hf.space/?key=<your key>` on the iPad. Add it to your Home Screen if you like.

Expect several minutes per song on the free CPU. YouTube/Instagram sometimes refuse downloads from hosting servers; if a link fails with a sign-in or bot error, add a secret `YTDLP_COOKIES` containing a Netscape-format `cookies.txt` from a browser where you're logged in (use a throwaway account; this carries account risk).

## GitHub Pages

Settings → Pages → Deploy from branch → `main` / `docs`.

## Notes

- Everything except vocals and drums is transcribed, so a sung section may add a few stray notes.
- Only download audio you have the right to use; this is meant for personal transcription practice.
