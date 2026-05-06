#!/usr/bin/env bash
# Adds "jat" command to your shell so you can run it from anywhere.
# Run once: bash scripts/install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LINK_PATH="/usr/local/bin/jat"

if [ -w "/usr/local/bin" ]; then
    ln -sf "$SCRIPT_DIR/jat.sh" "$LINK_PATH"
else
    sudo ln -sf "$SCRIPT_DIR/jat.sh" "$LINK_PATH"
fi

chmod +x "$SCRIPT_DIR/jat.sh"

# Install Python dependencies including chromadb
pip install -e . 2>/dev/null || pip3 install -e . 2>/dev/null
echo "[OK] Python dependencies installed."
echo "[NOTE] First run may download embedding models (~100MB)."

echo "[OK] 'jat' command installed. Type: jat"
