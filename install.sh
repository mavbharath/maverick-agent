#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV="$PROJECT_DIR/.venv"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/pip" install -e "$PROJECT_DIR"
printf '\nInstalled. Next:\n  ollama pull qwen2.5-coder:7b\n  %s doctor --repo /path/to/repo\n' "$PROJECT_DIR/run.sh"
