#!/usr/bin/env bash
set -euo pipefail

sudo systemctl disable --now ai-crypto-frontend.service || true
sudo systemctl disable --now ai-crypto-backend.service || true
sudo rm -f /etc/systemd/system/ai-crypto-frontend.service
sudo rm -f /etc/systemd/system/ai-crypto-backend.service
sudo systemctl daemon-reload

echo "LAN systemd services removed."
