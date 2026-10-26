#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV="$PROJECT_DIR/.venv"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed. See https://ollama.com/download" >&2
  exit 1
fi

if [ ! -x "$VENV/bin/local-coder" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -e "$PROJECT_DIR"
fi

exec "$VENV/bin/local-coder" "$@"
