#!/usr/bin/env bash
# Adds "jai" command to your shell so you can run it from anywhere.
# Run once: bash scripts/install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LINK_PATH="/usr/local/bin/jai"

if [ -w "/usr/local/bin" ]; then
    ln -sf "$SCRIPT_DIR/jai.sh" "$LINK_PATH"
else
    sudo ln -sf "$SCRIPT_DIR/jai.sh" "$LINK_PATH"
fi

chmod +x "$SCRIPT_DIR/jai.sh"
echo "[OK] 'jai' command installed. Type: jai"
