#!/usr/bin/env bash
# Generates a local TLS certificate in ./certs/ for HTTPS & WebXR on Meta Quest 2.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="${REPO_ROOT}/certs"
mkdir -p "${CERT_DIR}"

LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo '127.0.0.1')"
if [[ -z "${LAN_IP}" ]]; then
  LAN_IP="127.0.0.1"
fi

echo "Generating TLS certificate for localhost, 127.0.0.1, and LAN IP ${LAN_IP} ..."

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "${CERT_DIR}/key.pem" \
  -out "${CERT_DIR}/cert.pem" \
  -subj "/CN=${LAN_IP}" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:${LAN_IP}"

echo "Certificates written to:"
echo "  ${CERT_DIR}/cert.pem"
echo "  ${CERT_DIR}/key.pem"
