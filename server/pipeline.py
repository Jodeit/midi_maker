"""YouTube URL -> two-hand MIDI.  yt-dlp -> Demucs (drop vocals/drums) -> Transkun -> split at C4."""
import os, subprocess, sys, shutil
from pathlib import Path

import numpy as np
import pretty_midi
import soundfile as sf

SPLIT_PITCH = 60  # middle C: >= right hand, < left hand
KEEP_STEMS = ["piano", "other", "guitar", "bass"]  # everything but vocals/drums


def run(cmd, log):
    log(" ".join(map(str, cmd)))
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-600:])


def make_midi(url: str, workdir: Path, log=print, progress=lambda s: None, split=SPLIT_PITCH) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    bindir = Path(sys.executable).parent

    progress("Downloading audio")
    cmd = ["yt-dlp", "--no-playlist", "-x", "--audio-format", "wav",
           "-o", str(workdir / "audio.%(ext)s")]
    cookies = os.environ.get("YTDLP_COOKIES")  # optional: Netscape cookies.txt contents (hosted setups)
    if cookies:
        cf = workdir / "cookies.txt"
        cf.write_text(cookies)
        cmd += ["--cookies", str(cf)]
    run(cmd + [url], log)
    wav = workdir / "audio.wav"

    progress("Removing vocals")
    run([sys.executable, "-m", "demucs", "-n", "htdemucs_6s", "-o", str(workdir / "stems"), str(wav)], log)
    stems = workdir / "stems" / "htdemucs_6s" / "audio"
    mix, sr = None, None
    for name in KEEP_STEMS:
        x, sr = sf.read(stems / f"{name}.wav")
        mix = x if mix is None else mix + x
    novocals = workdir / "novocals.wav"
    sf.write(novocals, mix, sr)
    shutil.rmtree(workdir / "stems", ignore_errors=True)

    progress("Transcribing piano")
    raw = workdir / "raw.mid"
    run([str(bindir / "transkun"), str(novocals), str(raw), "--device", device()], log)

    progress("Splitting hands")
    src = pretty_midi.PrettyMIDI(str(raw))
    notes = sorted((n for i in src.instruments for n in i.notes), key=lambda n: n.start)
    out = pretty_midi.PrettyMIDI(initial_tempo=estimate_tempo(novocals))
    rh = pretty_midi.Instrument(0, name="Right Hand")
    lh = pretty_midi.Instrument(0, name="Left Hand")
    for n in notes:
        (rh if n.pitch >= split else lh).notes.append(n)
    out.instruments += [rh, lh]
    result = workdir / "output.mid"
    out.write(str(result))
    return result


def device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def estimate_tempo(path: Path) -> float:
    try:
        import librosa
        y, sr = librosa.load(str(path), sr=22050)
        t = float(np.atleast_1d(librosa.beat.beat_track(y=y, sr=sr)[0])[0])
        while t > 140: t /= 2
        while t < 60: t *= 2
        return round(t, 1)
    except Exception:
        return 90.0
