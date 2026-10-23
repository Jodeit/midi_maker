#!/usr/bin/env bash
# Starts the backend and a free Cloudflare tunnel, then prints a link to open on your iPad.
set -e
cd "$(dirname "$0")"
PAGE="https://jodeit.github.io/midi_maker/"
export MIDI_MAKER_KEY="${MIDI_MAKER_KEY:-$(python3 -c 'import secrets;print(secrets.token_urlsafe(12))')}"
export PORT="${PORT:-8000}"
PY="${PYTHON:-.venv/bin/python}"
"$PY" server/app.py > server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER $TUNNEL 2>/dev/null' EXIT
cloudflared tunnel --protocol http2 --url "http://localhost:$PORT" > tunnel.log 2>&1 &
TUNNEL=$!
for _ in $(seq 1 30); do
  URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' tunnel.log | head -1 || true)
  [ -n "$URL" ] && break; sleep 1
done
[ -z "$URL" ] && { echo "Tunnel did not start; see tunnel.log"; exit 1; }
# only print the link once the tunnel is actually connected to Cloudflare
for _ in $(seq 1 30); do
  grep -q "Registered tunnel connection" tunnel.log && break; sleep 1
done
grep -q "Registered tunnel connection" tunnel.log || { echo "Tunnel never connected; see tunnel.log"; exit 1; }
echo
echo "Open this on your iPad (it fills in the backend for you):"
echo "  ${PAGE}?backend=${URL}&key=${MIDI_MAKER_KEY}"
echo
echo "Keep this window open. Ctrl-C to stop."
wait $SERVER
