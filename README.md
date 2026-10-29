# Remon YT Downloader — macOS Multi-Platform Video & Audio Downloader

A dark, beginner-friendly macOS desktop app for downloading video and audio from **YouTube, Facebook, Instagram, and TikTok** with quality selection and save location control. Intended for Apple Silicon (M-series) Macs.

Use only for content you own, have permission to download, or are otherwise legally allowed to save. Follow each platform's Terms of Service and applicable copyright laws.

## Features

- **Multi-Platform Support**: Download video and audio from **YouTube** (Videos, Shorts), **Facebook** (Videos, Reels), **Instagram** (Reels, Posts), and **TikTok** (Videos, Audio).
- **Platform Selector & Auto-Detection**: Instant platform switching buttons (Auto Detect, YouTube, Facebook, Instagram, TikTok) and real-time URL detection.
- **Inspect Metadata**: View title, uploader, duration, thumbnail, and format counts before downloading.
- **Video Mode**: Choose resolution (4K, 2K, 1080p, 720p, 480p, 360p, or HD/SD) and **Codec** (H.264/AVC, VP9, AV1, HEVC, or Auto) with automatic stream matching, availability indicators, and fallback protection.
- **Audio Mode**: Extract high-quality audio to MP3 (320, 256, 192, 128 kbps), M4A, WAV, FLAC, AAC, or Original format.
- **Separate Location & Start**: Dedicated "Choose location" and "Start Download" buttons for full control over destination files.
- **Bundled Engines**: Uses bundled FFmpeg and QuickJS automatically so it runs self-contained on any Mac.
- **Browser Session Integration**: Automatic browser cookie integration (Chrome, Firefox, Brave, Edge, Safari) for platforms requiring verification.
- **Download progress**: Real-time progress bar, speed, ETA, and cancellation support.
- **Unlimited downloads**: No artificial limits, watermarks, or subscription paywalls.

## Important build vs. use distinction

The **end user** should only open the installed app. Creating the `.app` and `.dmg` is a separate build step that must be done on a Mac (preferably the target Apple Silicon Mac).

## Build on an Apple Silicon Mac

### One-time builder setup

1. Install Python 3.11 or 3.12 for Apple Silicon from https://www.python.org/downloads/macos/ .
2. Install Apple's Command Line Tools if PyInstaller or Qt needs a compiler/runtime component. Open Terminal and run:
   `xcode-select --install`
3. In Terminal, run the build script:
   `bash build_mac.sh`

### Create a DMG

After the app builds, run:
`bash make_dmg.sh`

Output: `dist/Remon-YT-Downloader.dmg`

### Install and launch

1. Double-click `Remon-YT-Downloader.dmg`.
2. Drag `Remon YT Downloader.app` to Applications.
3. Eject the disk image and open the app from Applications.
4. If macOS says the app is from an unidentified developer, that is because this locally built app is not Developer ID signed and notarized. For your own build, use Control-click > Open if macOS permits it, and only do this if you trust the source you built.

For a public download, sign and notarize the app with an Apple Developer ID certificate and Apple's notarization workflow. Signing/notarization require an Apple Developer account and credentials; do not put credentials in this project or share them.

## App usage

1. Choose a platform tab (**Auto Detect**, **YouTube**, **Facebook**, **Instagram**, or **TikTok**), or simply paste any link into the input box.
2. Click **Inspect media** to fetch title, uploader, duration, and stream formats.
3. Choose **Video** or **Audio** mode.
4. Pick a resolution (4K, 1080p, 720p, etc.) and video codec (H.264/AVC, VP9, AV1, or Auto), or choose audio format (MP3 with bitrate, M4A, WAV, FLAC, AAC, Original).
5. Click **Choose location** to pick your save folder and filename.
6. Click **Start Download**. Watch the real-time progress bar or click **Cancel** if needed.

## Troubleshooting

- **No formats appear / URL fails:** the source may be private, age-restricted, unavailable, or unsupported. Update yt-dlp by rebuilding with the latest version.
- **4K not listed:** quality depends on the source video and what YouTube makes available.
- **Merge/conversion error:** confirm FFmpeg is present in `ClipHarbor.app/Contents/Resources/bin/ffmpeg` in the packaged app.
- **macOS blocks launch:** unsigned builds may trigger Gatekeeper. For public distribution, Developer ID signing and notarization are strongly recommended.
- **Architecture:** this build is configured for Apple Silicon arm64. An Intel Mac build should be built separately on Intel or configured as a universal build and tested on both architectures.

## Project layout

- `clipharbor.py` — UI and download workflow.
- `requirements.txt` — Python dependencies.
- `ClipHarbor.spec` — PyInstaller app bundle configuration.
- `build_mac.sh` — build helper.
- `make_dmg.sh` — DMG helper.

## License notes

This project code is provided as a starter project. PySide6/Qt, yt-dlp, FFmpeg, and PyInstaller each have their own licenses and redistribution conditions. Review them before sharing a compiled application. FFmpeg builds may differ in codec configuration and licensing; choose a distribution build suitable for your use.
