#!/usr/bin/env bash
# Build a standalone single-file executable.
# Runtime dependencies (NOT bundled — install via your package manager):
#   xdotool   — for text injection on X11
#   xkb-switch — for layout switching (or setxkbmap as fallback)
#   ydotool   — optional, for Wayland text injection

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "▶ Installing Python dependencies..."
pip install -q -r requirements.txt

echo "▶ Building standalone executable..."
pyinstaller \
    --onefile \
    --noconsole \
    --name smooth_kl-switcher \
    main.py

echo ""
echo "✓ Done!  Binary: dist/smooth_kl-switcher"
echo ""
echo "Run with:  ./dist/smooth_kl-switcher"
echo ""
echo "Make sure xdotool and xkb-switch are installed:"
echo "  Ubuntu/Debian: sudo apt install xdotool xkb-switch"
echo "  Arch:          sudo pacman -S xdotool xkb-switch"
echo "  Fedora:        sudo dnf install xdotool xkb-switch"
