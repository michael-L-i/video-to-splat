#!/usr/bin/env bash
# Setup for video-to-splat on Apple Silicon macOS.
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1; }

need brew || { echo "Homebrew required: https://brew.sh"; exit 1; }
need ffmpeg || { say "Installing ffmpeg"; brew install ffmpeg; }
need uv || { say "Installing uv"; brew install uv; }

say "Syncing Python environment (fastapi, pycolmap, sharp-frames...)"
uv sync

# Brush splat trainer: prefer a from-source build (newer quality flags), else prebuilt release.
if [[ ! -x vendor/brush_src/target/release/brush && ! -x vendor/brush ]]; then
  if need cargo; then
    say "Building Brush from source (one-time, ~5-10 min)"
    [[ -d vendor/brush_src ]] || git clone --depth 1 https://github.com/ArthurBrussee/brush vendor/brush_src
    (cd vendor/brush_src && cargo build --release -p brush-app) || true
  fi
  if [[ ! -x vendor/brush_src/target/release/brush ]]; then
    say "Downloading Brush v0.3.0 prebuilt binary"
    curl -sL https://github.com/ArthurBrussee/brush/releases/download/v0.3.0/brush-app-aarch64-apple-darwin.tar.xz |
      tar xJ -C vendor
    mv vendor/brush-app-aarch64-apple-darwin/brush_app vendor/brush
    rm -rf vendor/brush-app-aarch64-apple-darwin
    chmod +x vendor/brush
  fi
fi

# Optional: splat cleanup/compression (.spz/.sog exports)
if need npm; then
  say "Priming splat-transform (optional, for cleanup + .spz/.sog export)"
  npx --yes @playcanvas/splat-transform --version >/dev/null 2>&1 || true
fi

say "Done. Start the app with:  ./run.sh   (then open http://127.0.0.1:8000)"
