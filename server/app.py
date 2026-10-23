"""Tiny job server. Run: python server/app.py   (env: MIDI_MAKER_KEY to fix the access key, PORT)"""
import os, secrets, shutil, threading, uuid
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, jsonify, request, send_file

from pipeline import make_midi

KEY = os.environ.get("MIDI_MAKER_KEY") or secrets.token_urlsafe(12)
ROOT = Path(__file__).resolve().parent.parent
JOBS_DIR = ROOT / "jobs"
DOCS = ROOT / "docs"
ALLOWED_HOSTS = ("youtube.com", "youtu.be", "instagram.com")
JOBS: dict = {}
LOCK = threading.Lock()  # one heavy job at a time
app = Flask(__name__)


@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Key"
    resp.headers["Access-Control-Allow-Private-Network"] = "true"
    return resp


@app.before_request
def auth():
    if request.method == "OPTIONS" or request.path == "/":
        return
    if (request.headers.get("X-Key") or request.args.get("key")) != KEY:
        return jsonify(error="bad key"), 401


@app.route("/")
def root():
    # same-Wi-Fi mode: serve the page from here so no tunnel or https is needed
    return send_file(DOCS / "index.html")


@app.route("/api/jobs", methods=["POST", "OPTIONS"])
def create():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    host = (urlparse(url).hostname or "").lower()
    if not any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS):
        return jsonify(error="Enter a YouTube or Instagram link"), 400
    jid = uuid.uuid4().hex[:10]
    JOBS[jid] = {"status": "queued", "step": "Queued", "error": None}
    threading.Thread(target=work, args=(jid, url, int(data.get("split", 60))), daemon=True).start()
    return jsonify(id=jid)


def work(jid, url, split):
    job = JOBS[jid]
    with LOCK:
        try:
            job.update(status="running")
            path = make_midi(url, JOBS_DIR / jid, log=print,
                             progress=lambda s: job.update(step=s), split=split)
            job.update(status="done", step="Done", file=str(path))
        except Exception as e:
            job.update(status="error", error=str(e))
        finally:
            for p in (JOBS_DIR / jid).glob("*.wav"):
                p.unlink(missing_ok=True)


@app.route("/api/jobs/<jid>")
def status(jid):
    j = JOBS.get(jid)
    if not j:
        return jsonify(error="unknown job"), 404
    return jsonify(status=j["status"], step=j["step"], error=j["error"])


@app.route("/api/jobs/<jid>/midi")
def midi(jid):
    j = JOBS.get(jid)
    if not j or j["status"] != "done":
        return jsonify(error="not ready"), 404
    return send_file(j["file"], mimetype="audio/midi", as_attachment=True, download_name="two_hands.mid")


if __name__ == "__main__":
    shutil.rmtree(JOBS_DIR, ignore_errors=True)
    JOBS_DIR.mkdir()
    port = int(os.environ.get("PORT", 8000))
    print(f"\n  Access key: {KEY}\n  Listening on http://localhost:{port}\n", flush=True)
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=port, threaded=True)
