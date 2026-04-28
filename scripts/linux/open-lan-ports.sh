#!/usr/bin/env bash
set -euo pipefail

if ! command -v ufw >/dev/null 2>&1; then
  echo "ufw is not installed. Nothing to configure."
  echo "If you use another firewall, allow TCP ports 5173 and 8000 only from your LAN."
  exit 0
fi

echo "Opening LAN-only access for ports 5173 and 8000..."
sudo ufw allow from 192.168.0.0/16 to any port 5173 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 8000 proto tcp
sudo ufw allow from 10.0.0.0/8 to any port 5173 proto tcp
sudo ufw allow from 10.0.0.0/8 to any port 8000 proto tcp
sudo ufw allow from 172.16.0.0/12 to any port 5173 proto tcp
sudo ufw allow from 172.16.0.0/12 to any port 8000 proto tcp

echo
sudo ufw status numbered || true
echo
echo "Done. Do not forward these ports from your router to the internet."
