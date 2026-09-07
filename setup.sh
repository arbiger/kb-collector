#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MLX_VENV="${MLX_WHISPER_VENV:-/Users/george/venv-mlx-whisper}"
MLX_BIN="${MLX_WHISPER_BIN:-$MLX_VENV/bin/mlx_whisper}"

echo "=== KB Collector setup ==="

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3 is required: $PYTHON_BIN" >&2
  exit 1
fi

if [ ! -x "$MLX_VENV/bin/python" ]; then
  echo "Creating isolated runtime at $MLX_VENV"
  "$PYTHON_BIN" -m venv "$MLX_VENV"
fi

echo "Installing collector dependencies into $MLX_VENV"
"$MLX_VENV/bin/python" -m pip install --upgrade pip
"$MLX_VENV/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt" mlx-whisper==0.4.3

echo "Checking the MLX runtime"
"$MLX_VENV/bin/python" -c 'import mlx_whisper; print("mlx-whisper import: OK")'
if [ ! -x "$MLX_BIN" ]; then
  echo "mlx_whisper executable not found at $MLX_BIN" >&2
  exit 1
fi

check_command() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    printf '%s: %s\n' "$name" "$(command -v "$name")"
  elif [ -x "$MLX_VENV/bin/$name" ]; then
    printf '%s: %s\n' "$name" "$MLX_VENV/bin/$name"
  else
    echo "$name is required but was not found. Install it with your system package manager." >&2
    return 1
  fi
}

echo "Checking external tools"
check_command yt-dlp
check_command ffmpeg
check_command ffprobe

if [ ! -f "$SCRIPT_DIR/.env" ]; then
  cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
  echo "Created $SCRIPT_DIR/.env from .env.example"
else
  echo "Preserved existing $SCRIPT_DIR/.env"
fi

echo "Setup complete. Supported audio engine: $MLX_BIN"
