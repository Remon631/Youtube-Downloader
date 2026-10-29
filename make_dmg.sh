#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
APP="dist/Remon YT Downloader.app"
DMG="dist/Remon-YT-Downloader.dmg"
if [[ ! -d "$APP" ]]; then
  echo "Build the app first with: bash build_mac.sh"
  exit 1
fi
mkdir -p "$APP/Contents/MacOS/bin" "$APP/Contents/Frameworks/bin" "$APP/Contents/Resources/bin"
cp -f bin/ffmpeg bin/qjs "$APP/Contents/MacOS/bin/" 2>/dev/null || true
cp -f bin/ffmpeg bin/qjs "$APP/Contents/Frameworks/bin/" 2>/dev/null || true
cp -f bin/ffmpeg bin/qjs "$APP/Contents/Resources/bin/" 2>/dev/null || true
chmod 755 "$APP/Contents/MacOS/bin/"* "$APP/Contents/Frameworks/bin/"* "$APP/Contents/Resources/bin/"* 2>/dev/null || true

echo "Setting permissions and codesigning app bundle..."
chmod -R 755 "$APP"
xattr -cr "$APP" 2>/dev/null || true
codesign --force --deep --sign - "$APP"

mkdir -p dist/dmg-staging
rm -rf dist/dmg-staging/*
cp -R "$APP" dist/dmg-staging/
ln -s /Applications dist/dmg-staging/Applications
if [[ -f "logo/RYD.icns" ]]; then
  cp "logo/RYD.icns" dist/dmg-staging/.VolumeIcon.icns
  SetFile -c icnC dist/dmg-staging/.VolumeIcon.icns 2>/dev/null || true
  SetFile -a C dist/dmg-staging 2>/dev/null || true
fi
rm -f "$DMG"
hdiutil create -volname "Remon YT Downloader" -srcfolder dist/dmg-staging -ov -format UDZO "$DMG"
echo "Created: $DMG"
