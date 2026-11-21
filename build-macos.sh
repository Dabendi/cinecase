#!/usr/bin/env bash
# Build the macOS desktop app (Apple Silicon or Intel).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

FF_TAG="b6.1.1"
case "$(uname -m)" in
  arm64) ARCH="arm64" ;;
  x86_64) ARCH="x64" ;;
  *) echo "Unsupported architecture: $(uname -m)"; exit 1 ;;
esac

VENDOR="$ROOT/vendor/ffmpeg-macos-$ARCH"
mkdir -p "$VENDOR"
BASE="https://github.com/eugeneware/ffmpeg-static/releases/download/$FF_TAG"

if [ ! -x "$VENDOR/ffmpeg" ]; then
  echo "Downloading ffmpeg (darwin-$ARCH)..."
  curl -L --fail "$BASE/ffmpeg-darwin-$ARCH.gz" | gunzip > "$VENDOR/ffmpeg"
  chmod +x "$VENDOR/ffmpeg"
fi
if [ ! -x "$VENDOR/ffprobe" ]; then
  echo "Downloading ffprobe (darwin-$ARCH)..."
  curl -L --fail "$BASE/ffprobe-darwin-$ARCH.gz" | gunzip > "$VENDOR/ffprobe"
  chmod +x "$VENDOR/ffprobe"
fi
if [ ! -f "$VENDOR/LICENSE.txt" ]; then
  curl -L --fail "$BASE/darwin-$ARCH.LICENSE" -o "$VENDOR/LICENSE.txt" || true
fi

ICON="$ROOT/build/cinecase.icns"
if [ ! -f "$ICON" ]; then
  ICONSET="$ROOT/build/cinecase.iconset"
  rm -rf "$ICONSET"
  mkdir -p "$ICONSET"
  SRC="$ROOT/assets/cinecase-1024.png"
  sips -z 16 16 "$SRC" --out "$ICONSET/icon_16x16.png" >/dev/null
  sips -z 32 32 "$SRC" --out "$ICONSET/icon_16x16@2x.png" >/dev/null
  sips -z 32 32 "$SRC" --out "$ICONSET/icon_32x32.png" >/dev/null
  sips -z 64 64 "$SRC" --out "$ICONSET/icon_32x32@2x.png" >/dev/null
  sips -z 128 128 "$SRC" --out "$ICONSET/icon_128x128.png" >/dev/null
  sips -z 256 256 "$SRC" --out "$ICONSET/icon_128x128@2x.png" >/dev/null
  sips -z 256 256 "$SRC" --out "$ICONSET/icon_256x256.png" >/dev/null
  sips -z 512 512 "$SRC" --out "$ICONSET/icon_256x256@2x.png" >/dev/null
  sips -z 512 512 "$SRC" --out "$ICONSET/icon_512x512.png" >/dev/null
  sips -z 1024 1024 "$SRC" --out "$ICONSET/icon_512x512@2x.png" >/dev/null
  iconutil -c icns "$ICONSET" -o "$ICON"
fi

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  python3 -m venv "$ROOT/.venv"
fi
PY="$ROOT/.venv/bin/python"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r "$ROOT/requirements-desktop.txt"

"$PY" -m PyInstaller --noconfirm --clean --windowed --onedir --name CineCase \
  --osx-bundle-identifier com.cinecase.app \
  --icon "$ICON" \
  --add-data "web:web" \
  --add-data "config.example.json:." \
  --add-data "assets:assets" \
  --add-data "$VENDOR:ffmpeg" \
  --hidden-import server \
  --hidden-import scan \
  --hidden-import webview.platforms.cocoa \
  --collect-data webview \
  "$ROOT/desktop.py"

APP="$ROOT/dist/CineCase.app"
find "$APP" -type f \( -name ffmpeg -o -name ffprobe \) -path '*ffmpeg*' -exec chmod +x {} \;
codesign --force --deep --sign - "$APP"

STAGE="$ROOT/dist/macos-$ARCH"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
cp "$ROOT/README-FIRST-macos.txt" "$ROOT/THIRD_PARTY_NOTICES.md" "$ROOT/config.example.json" "$STAGE/"
(
  cd "$ROOT/dist"
  rm -f "CineCase-macos-$ARCH.zip"
  zip -qry "CineCase-macos-$ARCH.zip" "macos-$ARCH"
)
echo "Built: $ROOT/dist/CineCase-macos-$ARCH.zip"
