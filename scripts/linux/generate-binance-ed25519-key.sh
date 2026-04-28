#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KEY_DIR="$ROOT/secrets"
PRIVATE_KEY="$KEY_DIR/binance_ed25519_private.pem"
PUBLIC_KEY="$KEY_DIR/binance_ed25519_public.pem"

mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

if [[ -f "$PRIVATE_KEY" || -f "$PUBLIC_KEY" ]]; then
  echo "Key files already exist:"
  echo "  $PRIVATE_KEY"
  echo "  $PUBLIC_KEY"
  echo "Move or delete them if you want to generate a new pair."
  exit 1
fi

openssl genpkey -algorithm ed25519 -out "$PRIVATE_KEY"
openssl pkey -in "$PRIVATE_KEY" -pubout -out "$PUBLIC_KEY"
chmod 600 "$PRIVATE_KEY"
chmod 644 "$PUBLIC_KEY"

echo
echo "Generated Binance Ed25519 key pair."
echo
echo "Private key, keep on server only:"
echo "  $PRIVATE_KEY"
echo
echo "Public key, paste this into Binance API creation:"
echo "  $PUBLIC_KEY"
echo
cat "$PUBLIC_KEY"
echo
echo "After Binance gives you the API key, put this in backend/.env:"
echo "  BINANCE_TESTNET_KEY_TYPE=ed25519"
echo "  BINANCE_TESTNET_API_KEY=your_binance_api_key"
echo "  BINANCE_TESTNET_PRIVATE_KEY_PATH=$PRIVATE_KEY"
