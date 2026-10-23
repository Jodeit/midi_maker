"""Tiny job server. Run: python server/app.py   (env: MIDI_MAKER_KEY to fix the access key, PORT)"""
import base64, json, os, queue, secrets, shutil, threading, uuid
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, Response, jsonify, request, send_file, stream_with_context

import models  # noqa: F401  (also enables OS certificate trust)
from pipeline import make_midi

KEY = os.environ.get("MIDI_MAKER_KEY") or secrets.token_urlsafe(12)
ROOT = Path(__file__).resolve().parent.parent
JOBS_DIR = Path(os.environ.get("MIDI_MAKER_JOBS", ROOT / "jobs"))
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
    if not check_url(url):
        return jsonify(error="Enter a YouTube or Instagram link"), 400
    jid = uuid.uuid4().hex[:10]
    JOBS[jid] = {"status": "queued", "step": "Queued", "error": None}
    threading.Thread(target=work, args=(jid, url), daemon=True).start()
    return jsonify(id=jid)


def work(jid, url):
    job = JOBS[jid]
    with LOCK:
        try:
            job.update(status="running")
            path = make_midi(url, JOBS_DIR / jid, log=print,
                             progress=lambda s: job.update(step=s))
            job.update(status="done", step="Done", file=str(path))
        except Exception as e:
            job.update(status="error", error=str(e))
        finally:
            for p in (JOBS_DIR / jid).glob("*.wav"):
                p.unlink(missing_ok=True)


def check_url(url):
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


@app.route("/api/convert", methods=["POST", "OPTIONS"])
def convert():
    """One request that streams progress lines and ends with the MIDI (base64).

    Built for AWS Lambda (no shared state between requests, so no job polling) and
    safe on iPad: data keeps flowing, so Safari doesn't time the request out.
    """
    if request.method == "OPTIONS":
        return "", 204
    url = ((request.get_json(silent=True) or {}).get("url") or "").strip()
    if not check_url(url):
        return jsonify(error="Enter a YouTube or Instagram link"), 400
    events = queue.Queue()
    jid = uuid.uuid4().hex[:10]

    def run():
        with LOCK:
            try:
                path = make_midi(url, JOBS_DIR / jid, log=print,
                                 progress=lambda s: events.put({"step": s}))
                events.put({"done": True, "midi": base64.b64encode(Path(path).read_bytes()).decode()})
            except Exception as e:
                events.put({"error": str(e)})
            finally:
                shutil.rmtree(JOBS_DIR / jid, ignore_errors=True)

    threading.Thread(target=run, daemon=True).start()

    def stream():
        while True:
            try:
                ev = events.get(timeout=5)
            except queue.Empty:
                yield json.dumps({"ping": 1}) + "\n"  # keep the connection busy
                continue
            yield json.dumps(ev) + "\n"
            if ev.get("done") or ev.get("error"):
                return

    return Response(stream_with_context(stream()), mimetype="application/x-ndjson",
                    headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


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
    JOBS_DIR.mkdir(parents=True)
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") and not os.environ.get("MIDI_MAKER_KEY"):
        raise SystemExit("Set MIDI_MAKER_KEY on the Lambda function")
    port = int(os.environ.get("PORT", 8000))
    print(f"\n  Access key: {KEY}\n  Listening on http://localhost:{port}\n", flush=True)
    # HTTP/1.1 makes the dev server send streamed responses chunked, which the Lambda
    # Web Adapter needs in order to pass progress through instead of buffering it
    from werkzeug.serving import WSGIRequestHandler
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=port, threaded=True)
