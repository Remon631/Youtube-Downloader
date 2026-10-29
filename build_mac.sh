#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

ARCH="$(uname -m)"
if [[ "$ARCH" != "arm64" ]]; then
  echo "This project is configured for Apple Silicon (arm64). Build on an M-series Mac."
  exit 1
fi

PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ is required"' || {
  echo "Install Python 3.11 or 3.12 for macOS from python.org, then rerun this script."
  exit 1
}

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

mkdir -p bin dist
if [[ ! -x bin/ffmpeg ]]; then
  echo ""
  echo "FFmpeg is not bundled in the source ZIP because redistribution terms and build variants differ."
  echo "Choose an ARM64 FFmpeg build you are licensed to redistribute, then place the executable at:"
  echo "  $(pwd)/bin/ffmpeg"
  echo ""
  echo "For a personal local build, Homebrew is a convenient option: brew install ffmpeg"
  echo "Then copy it here with: cp \"$(command -v ffmpeg)\" bin/ffmpeg"
  echo "If Homebrew is not installed, see https://brew.sh/"
  echo ""
  read -r -p "Press Enter after placing an executable FFmpeg at bin/ffmpeg, or Ctrl+C to stop. "
fi

if [[ ! -x bin/ffmpeg ]]; then
  echo "FFmpeg missing or not executable: bin/ffmpeg"
  exit 1
fi

python -m PyInstaller --noconfirm --clean ClipHarbor.spec
echo ""
echo "Build complete: dist/Remon YT Downloader.app"
echo "Test the app on this Mac before sharing it."
