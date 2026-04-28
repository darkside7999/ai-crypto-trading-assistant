#!/usr/bin/env bash
set -euo pipefail

systemctl status ai-crypto-backend.service ai-crypto-frontend.service --no-pager

SERVER_IP="$(hostname -I | awk '{print $1}')"
echo
echo "Frontend LAN URL: http://${SERVER_IP:-SERVER_IP}:5173"
echo "Backend health:   http://${SERVER_IP:-SERVER_IP}:8000/health"
