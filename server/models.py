"""Fetch the Transkun V2 Aug piano model (the Transkun author's augmentation-trained checkpoint).

Source and checksum match the pins used by https://github.com/mason369/music-to-midi.
"""
import hashlib, os, urllib.request, zipfile
from pathlib import Path

try:  # trust the OS certificate store (corporate TLS inspection, e.g. Zscaler)
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = Path(os.environ.get("MIDI_MAKER_MODELS", ROOT / "models")) / "transkun_v2_aug"
FILE_ID = "1Hg5ua8vYdtg1Y-MnXD0mLyhRK9Srd7hm"
URL = f"https://drive.usercontent.google.com/download?id={FILE_ID}&export=download&confirm=t"
SHA256 = "f61ebf6467d89081fde9728b659895a3e3d65b4c89516964178967167fae6590"
SIZE = 50_694_377
INNER = "checkpointMSimplerAug"


def paths():
    d = MODEL_DIR / INNER
    return d / "checkpoint.pt", d / "model.conf"


def ensure(log=print):
    """Return (weight, conf), downloading and verifying the model on first use."""
    weight, conf = paths()
    if weight.exists() and conf.exists():
        return weight, conf
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    archive = MODEL_DIR / "aug.zip"
    log("Downloading Transkun V2 Aug model (50 MB)")
    with urllib.request.urlopen(URL, timeout=120) as r, open(archive, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if archive.stat().st_size != SIZE or digest != SHA256:
        archive.unlink(missing_ok=True)
        raise RuntimeError("Transkun V2 Aug download failed its checksum")
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():  # refuse paths that escape the target folder
            if not (MODEL_DIR / name).resolve().is_relative_to(MODEL_DIR.resolve()):
                raise RuntimeError("unsafe path in model archive")
        z.extractall(MODEL_DIR)
    archive.unlink(missing_ok=True)
    if not (weight.exists() and conf.exists()):
        raise RuntimeError("model archive missing expected files")
    return weight, conf


if __name__ == "__main__":
    print(ensure())
