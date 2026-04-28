#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
  echo "Run this script as your normal user, not directly as root."
  echo "It will call sudo only when writing systemd services."
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
USER_NAME="$(id -un)"
GROUP_NAME="$(id -gn)"
NPM_BIN="$(command -v npm || true)"
NPM_DIR="$(dirname "$NPM_BIN")"

if [[ -z "$NPM_BIN" ]]; then
  echo "npm was not found. Install Node.js/npm first."
  exit 1
fi

"$ROOT/scripts/setup-local.sh"

set_env_line() {
  local file="$1"
  local key="$2"
  local value="$3"
  "$BACKEND/.venv/bin/python" - "$file" "$key" "$value" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
prefix = f"{key}="
found = False
next_lines = []
for line in lines:
    if line.startswith(prefix):
        next_lines.append(f"{key}={value}")
        found = True
    else:
        next_lines.append(line)
if not found:
    next_lines.append(f"{key}={value}")
path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")
PY
}

set_env_line "$BACKEND/.env" "DATABASE_URL" "sqlite:///./dev_trading.db"
set_env_line "$BACKEND/.env" "AUTO_START_SCHEDULER" "true"
set_env_line "$BACKEND/.env" "CORS_ORIGIN_REGEX" '^http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):5173$'
set_env_line "$FRONTEND/.env" "VITE_API_BASE_URL" ""

cd "$FRONTEND"
npm run build

BACKEND_SERVICE="$(mktemp)"
FRONTEND_SERVICE="$(mktemp)"

cat > "$BACKEND_SERVICE" <<EOF
[Unit]
Description=AI Crypto Trading Assistant Backend
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$USER_NAME
Group=$GROUP_NAME
WorkingDirectory=$BACKEND
EnvironmentFile=$BACKEND/.env
ExecStart=$BACKEND/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
TimeoutStopSec=20
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

cat > "$FRONTEND_SERVICE" <<EOF
[Unit]
Description=AI Crypto Trading Assistant Frontend
Wants=network-online.target ai-crypto-backend.service
After=network-online.target ai-crypto-backend.service

[Service]
Type=simple
User=$USER_NAME
Group=$GROUP_NAME
WorkingDirectory=$FRONTEND
Environment=PATH=$NPM_DIR:/usr/local/bin:/usr/bin:/bin
ExecStart=$NPM_BIN run preview -- --host 0.0.0.0 --port 5173
Restart=always
RestartSec=5
TimeoutStopSec=20
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

sudo cp "$BACKEND_SERVICE" /etc/systemd/system/ai-crypto-backend.service
sudo cp "$FRONTEND_SERVICE" /etc/systemd/system/ai-crypto-frontend.service
rm -f "$BACKEND_SERVICE" "$FRONTEND_SERVICE"

sudo systemctl daemon-reload
sudo systemctl enable --now ai-crypto-backend.service
sudo systemctl enable --now ai-crypto-frontend.service

if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow from 192.168.0.0/16 to any port 5173 proto tcp || true
  sudo ufw allow from 192.168.0.0/16 to any port 8000 proto tcp || true
  sudo ufw allow from 10.0.0.0/8 to any port 5173 proto tcp || true
  sudo ufw allow from 10.0.0.0/8 to any port 8000 proto tcp || true
  sudo ufw allow from 172.16.0.0/12 to any port 5173 proto tcp || true
  sudo ufw allow from 172.16.0.0/12 to any port 8000 proto tcp || true
fi

SERVER_IP="$(hostname -I | awk '{print $1}')"
echo
echo "LAN services installed and started."
echo "Open from your WiFi devices: http://${SERVER_IP:-SERVER_IP}:5173"
echo
echo "Status:"
echo "  systemctl status ai-crypto-backend ai-crypto-frontend"
echo "Logs:"
echo "  journalctl -u ai-crypto-backend -f"
echo "  journalctl -u ai-crypto-frontend -f"
