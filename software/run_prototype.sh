#!/usr/bin/env bash
# Starts the Main Server (HTTP :8000 + HTTPS :8443 for Quest 2 WebXR, one shared state)
# and the Camera Simulator (:8081).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PY="${SCRIPT_DIR}/.venv/bin/python"

if [[ ! -x "${VENV_PY}" ]]; then
  echo "Creating Python virtual environment in software/.venv ..."
  python3 -m venv "${SCRIPT_DIR}/.venv"
  "${SCRIPT_DIR}/.venv/bin/pip" install -r "${SCRIPT_DIR}/requirements.txt"
fi

if [[ ! -f "${REPO_ROOT}/certs/cert.pem" ]]; then
  bash "${SCRIPT_DIR}/generate_cert.sh"
fi

LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo '127.0.0.1')"

cleanup() {
  echo ""
  echo "Stopping prototype servers..."
  kill $(jobs -p) 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 1. Main Server: HTTP :8000 (browser, camera ingest, heat sensor ingest) and
#    HTTPS :8443 (Quest 2 WebXR) in ONE process, so both show the same live data.
"${VENV_PY}" "${SCRIPT_DIR}/server/main.py" \
  --host 0.0.0.0 \
  --port 8000 \
  --https-port 8443 \
  --ssl-certfile "${REPO_ROOT}/certs/cert.pem" \
  --ssl-keyfile "${REPO_ROOT}/certs/key.pem" &

sleep 1

# 2. Camera Simulator on :8081 (pushes frames to :8000/ws/camera and serves :8081/stream).
#    Its fake heat values are ignored as soon as the real MLX90614 posts to /api/sensor.
"${VENV_PY}" "${SCRIPT_DIR}/camera_sim/simulator.py" \
  --host 0.0.0.0 \
  --port 8081 \
  --push "ws://127.0.0.1:8000/ws/camera" &

echo "=================================================================="
echo "Marshall Video & WebXR Prototype Running!"
echo "  - Desktop / Phone (HTTP):  http://${LAN_IP}:8000"
echo "  - Meta Quest 2 (HTTPS/VR): https://${LAN_IP}:8443"
echo "  - Camera Simulator MJPEG:  http://${LAN_IP}:8081/stream"
echo "  - Heat sensor ingest:      POST http://${LAN_IP}:8000/api/sensor"
echo "Press Ctrl+C to stop all servers."
echo "=================================================================="

wait
