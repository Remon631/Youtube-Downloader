import os
import sys
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import Qt, QThread, Signal, QSize, QUrl, QSettings
from PySide6.QtGui import QFont, QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QComboBox, QRadioButton, QButtonGroup,
    QProgressBar, QMessageBox, QFileDialog, QStackedWidget, QScrollArea,
    QGridLayout, QCheckBox, QSizePolicy
)


def resource_path(*parts):
    """Find bundled resources in a PyInstaller app, macOS bundle, or the source tree."""
    if hasattr(sys, "_MEIPASS"):
        meipass_target = Path(sys._MEIPASS).joinpath(*parts)
        if meipass_target.exists():
            return meipass_target

    exe_dir = Path(sys.executable).resolve().parent
    file_dir = Path(__file__).resolve().parent

    search_dirs = [
        file_dir,
        file_dir.parent.joinpath("Frameworks"),
        file_dir.parent.joinpath("MacOS"),
        file_dir.parent.joinpath("Resources"),
        exe_dir,
        exe_dir.parent.joinpath("Frameworks"),
        exe_dir.parent.joinpath("MacOS"),
        exe_dir.parent.joinpath("Resources"),
    ]

    for d in search_dirs:
        cand = d.joinpath(*parts)
        if cand.exists():
            return cand

    return file_dir.joinpath(*parts)


APP_NAME = "Remon YT Downloader V3.01"
_ytdlp_cache = None


def get_ytdlp():
    global _ytdlp_cache
    if _ytdlp_cache is None:
        import yt_dlp
        _ytdlp_cache = yt_dlp
    return _ytdlp_cache


def ffmpeg_location():
    candidates = [
        resource_path("bin", "ffmpeg"),
        resource_path("bin", "ffmpeg.exe"),
        Path(sys.executable).resolve().parent / "ffmpeg",
        Path("/opt/homebrew/bin/ffmpeg"),
        Path("/usr/local/bin/ffmpeg"),
        shutil.which("ffmpeg"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return str(Path(candidate).resolve().parent)
    return None


PLATFORMS = {
    "auto": {
        "id": "auto",
        "name": "Auto Detect",
        "badge": "AUTO",
        "icon": "✦",
        "placeholder": "Paste a YouTube, Facebook, Instagram, or TikTok link…",
        "color": "#8B7CFF",
        "bg": "#222038",
        "border": "#4C4477",
    },
    "youtube": {
        "id": "youtube",
        "name": "YouTube",
        "badge": "YOUTUBE",
        "icon": "▶",
        "placeholder": "Paste a YouTube video, shorts, or watch link…",
        "color": "#FF4D4D",
        "bg": "#381E22",
        "border": "#752B35",
    },
    "facebook": {
        "id": "facebook",
        "name": "Facebook",
        "badge": "FACEBOOK",
        "icon": "f",
        "placeholder": "Paste a Facebook video, reel, or watch link…",
        "color": "#3B82F6",
        "bg": "#1C2A44",
        "border": "#284A80",
    },
    "instagram": {
        "id": "instagram",
        "name": "Instagram",
        "badge": "INSTAGRAM",
        "icon": "📷",
        "placeholder": "Paste an Instagram reel, video, or post link…",
        "color": "#E1306C",
        "bg": "#3A1F2D",
        "border": "#7A2E4E",
    },
    "tiktok": {
        "id": "tiktok",
        "name": "TikTok",
        "badge": "TIKTOK",
        "icon": "🎵",
        "placeholder": "Paste a TikTok video or audio link…",
        "color": "#00F2FE",
        "bg": "#14303B",
        "border": "#1B5667",
    },
}


def detect_platform(url):
    """Detect platform from URL: returns 'youtube', 'facebook', 'instagram', 'tiktok', 'other', or None."""
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return None
        host = (parsed.hostname or "").lower()
        if host == "youtu.be" or host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
            return "youtube"
        if host in ("fb.watch", "fb.com", "fb.gg") or host.endswith("facebook.com") or host.endswith("facebookcorewwwi.onion"):
            return "facebook"
        if host == "instagr.am" or host.endswith("instagram.com"):
            return "instagram"
        if host == "tiktok.com" or host.endswith(".tiktok.com"):
            return "tiktok"
        return "other"
    except Exception:
        return None


def is_valid_url(url, required_platform="auto"):
    """Check if the URL is valid and matches the selected platform filter."""
    plat = detect_platform(url)
    if not plat:
        return False
    if required_platform and required_platform != "auto":
        return plat == required_platform
    return True


def pretty_duration(seconds):
    if not seconds:
        return "Duration unavailable"
    try:
        seconds = int(seconds)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    except Exception:
        return "Duration unavailable"


def format_bytes(num_bytes):
    """Format bytes to human-readable string (e.g. 14.5 MB)."""
    if not num_bytes or num_bytes <= 0:
        return ""
    try:
        num = float(num_bytes)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if num < 1024.0 or unit == "TB":
                return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} B"
            num /= 1024.0
    except Exception:
        return ""
    return ""


_detected_browser_cache = None


def js_engine_location():
    """Find a JavaScript runtime (quickjs, node, deno) for challenges."""
    candidates = [
        ("quickjs", resource_path("bin", "qjs")),
        ("quickjs", resource_path("bin", "quickjs")),
        ("quickjs", Path("/opt/homebrew/bin/qjs")),
        ("quickjs", shutil.which("qjs")),
        ("node", resource_path("bin", "node")),
        ("node", shutil.which("node")),
        ("node", Path("/opt/homebrew/bin/node")),
        ("node", Path("/usr/local/bin/node")),
    ]
    for runtime, candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return runtime, str(Path(candidate).resolve())
    return None, None


def get_available_browser_cookies():
    """Find the first available browser with accessible cookies on this system."""
    global _detected_browser_cache
    if _detected_browser_cache is not None:
        return _detected_browser_cache or None

    try:
        from yt_dlp.cookies import extract_cookies_from_browser
        for browser in ("chrome", "firefox", "brave", "edge", "safari", "chromium", "opera", "vivaldi"):
            try:
                jar = extract_cookies_from_browser(browser)
                if jar and len(jar) > 0:
                    _detected_browser_cache = browser
                    return browser
            except Exception:
                continue
    except Exception:
        pass

    _detected_browser_cache = ""
    return None


def apply_session_opts(opts, url=None, use_cookies=False):
    """Enhance yt-dlp options with JS runtime, optional browser cookies, and modern browser headers."""
    runtime, engine_bin = js_engine_location()
    if runtime and engine_bin:
        opts["js_runtimes"] = {runtime: {"path": engine_bin}}

    if use_cookies:
        browser = get_available_browser_cookies()
        if browser:
            opts["cookiesfrombrowser"] = (browser,)

    opts["http_headers"] = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    return opts


CODEC_REGEX_MAP = {
    "h264": r"(?i)avc1|h264",
    "vp9": r"(?i)vp0?9",
    "av1": r"(?i)av0?1",
    "hevc": r"(?i)hev1|hvc1|h265",
    "mp4v": r"(?i)mp4v",
}


def classify_vcodec(vcodec):
    """Normalize video codec string to a category key and user-friendly name."""
    if not vcodec or vcodec == "none":
        return None, None
    vc = str(vcodec).lower().strip()
    if vc.startswith("avc1") or vc.startswith("h264") or "h.264" in vc or "avc" in vc:
        return "h264", "H.264 / AVC"
    if vc.startswith("vp09") or vc.startswith("vp9") or "vp9" in vc:
        return "vp9", "VP9"
    if vc.startswith("av01") or vc.startswith("av1") or "av1" in vc:
        return "av1", "AV1"
    if vc.startswith("hev1") or vc.startswith("hvc1") or vc.startswith("h265") or "hevc" in vc:
        return "hevc", "H.265 / HEVC"
    if "mp4v" in vc:
        return "mp4v", "MPEG-4"
    return "other", vc.split(".")[0].upper()


class InspectWorker(QThread):
    finished_info = Signal(dict)
    failed = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def _extract_with_opts(self, use_cookies=False):
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        apply_session_opts(opts, self.url, use_cookies=use_cookies)
        with get_ytdlp().YoutubeDL(opts) as ydl:
            return ydl.extract_info(self.url, download=False)

    def run(self):
        try:
            plat = detect_platform(self.url) or "other"
            info = None
            last_err = None

            # Strategy for maximum format discovery:
            # - YouTube: start WITHOUT cookies. YouTube accounts often get enrolled in SABR experiments
            #   which strip adaptive streams down to 360p or error out.
            #   If age-restricted/login is required, retry with browser cookies.
            # - Facebook/Instagram/TikTok: browser cookies help with private/restricted posts.
            cookie_attempts = [False, True] if plat == "youtube" else [True, False]
            used_cookie_mode = False

            for use_cookies in cookie_attempts:
                try:
                    res = self._extract_with_opts(use_cookies=use_cookies)
                    if res:
                        if "entries" in res and res["entries"]:
                            entries = [e for e in res["entries"] if e]
                            if entries:
                                res = entries[0]
                        fmts = res.get("formats", [])
                        video_fmts = [f for f in fmts if f.get("vcodec") and f.get("vcodec") != "none"]
                        info = res
                        used_cookie_mode = use_cookies
                        # If without cookies on YouTube returned only <= 1 video format (e.g. 360p fallback),
                        # try with cookies to see if higher quality streams or authenticated formats are unlocked
                        if plat == "youtube" and not use_cookies and len(video_fmts) <= 1:
                            continue
                        break
                except Exception as e:
                    last_err = e
                    continue

            if not info:
                if last_err:
                    raise last_err
                raise RuntimeError("No media information could be retrieved for this URL.")

            duration_sec = info.get("duration")
            formats = []
            has_hd = False
            has_sd = False

            for f in info.get("formats", []):
                fid = str(f.get("format_id") or "")
                if not fid:
                    continue
                fid_lower = fid.lower()
                if "hd" in fid_lower:
                    has_hd = True
                if "sd" in fid_lower:
                    has_sd = True

                h = f.get("height")
                if not h and f.get("resolution"):
                    res_str = str(f.get("resolution"))
                    m = re.search(r'(\d+)[xX](\d+)', res_str)
                    if m:
                        h = min(int(m.group(1)), int(m.group(2)))

                vcodec = f.get("vcodec") or "none"
                acodec = f.get("acodec") or "none"
                filesize = f.get("filesize") or f.get("filesize_approx")
                if not filesize and f.get("tbr") and duration_sec:
                    try:
                        filesize = int(float(f["tbr"]) * 1000 / 8 * float(duration_sec))
                    except Exception:
                        pass

                formats.append({
                    "format_id": fid,
                    "height": h,
                    "width": f.get("width"),
                    "resolution": f.get("resolution") or (f"{f.get('width')}x{h}" if f.get("width") and h else (f"{h}p" if h else "")),
                    "ext": f.get("ext") or "",
                    "vcodec": vcodec,
                    "acodec": acodec,
                    "filesize": filesize,
                    "abr": f.get("abr"),
                    "vbr": f.get("vbr"),
                    "tbr": f.get("tbr"),
                    "fps": f.get("fps"),
                    "note": f.get("format_note") or "",
                    "has_audio": bool(acodec and acodec != "none"),
                    "has_video": bool(vcodec and vcodec != "none"),
                })

            raw_title = info.get("title") or info.get("description") or "Untitled media"
            clean_title = raw_title.split("\n")[0].strip() or "Untitled media"
            uploader = info.get("uploader") or info.get("channel") or info.get("creator") or ""
            has_audio = any(f["has_audio"] for f in formats)

            result = {
                "title": clean_title,
                "duration": pretty_duration(duration_sec),
                "duration_seconds": duration_sec,
                "thumbnail": info.get("thumbnail") or "",
                "formats": formats,
                "webpage_url": info.get("webpage_url") or self.url,
                "platform": plat,
                "uploader": uploader,
                "has_hd": has_hd,
                "has_sd": has_sd,
                "has_audio": has_audio,
                "used_cookies": used_cookie_mode,
            }
            self.finished_info.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


class DownloadWorker(QThread):
    progress = Signal(dict)
    completed = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, url, mode, quality, audio_format, audio_bitrate, output_path,
                 codec="best", container="mp4", include_audio=True, specific_format_id=None,
                 use_cookies=False):
        super().__init__()
        self.url = url
        self.mode = mode
        self.quality = quality
        self.codec = codec or "best"
        self.container = (container or "mp4").lower()
        self.include_audio = include_audio
        self.specific_format_id = specific_format_id
        self.audio_format = audio_format
        self.audio_bitrate = audio_bitrate
        self.output_path = output_path
        self.use_cookies = use_cookies
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def hook(self, data):
        if self._cancel_requested:
            raise get_ytdlp().utils.DownloadError("CLIPHARBOR_CANCELLED")
        status = data.get("status")
        info = {
            "status": status,
            "downloaded": data.get("downloaded_bytes", 0),
            "total": data.get("total_bytes") or data.get("total_bytes_estimate") or 0,
            "speed": data.get("speed"),
            "eta": data.get("eta"),
            "filename": data.get("filename", ""),
        }
        self.progress.emit(info)

    def run(self):
        try:
            ffmpeg_dir = ffmpeg_location()
            if not ffmpeg_dir:
                raise RuntimeError("FFmpeg was not found. Please ensure FFmpeg is installed or bundled.")
            chosen_path = Path(self.output_path).expanduser().resolve()
            chosen_path.parent.mkdir(parents=True, exist_ok=True)
            outtmpl = str(chosen_path.with_suffix("")) + ".%(ext)s"
            opts = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "outtmpl": outtmpl,
                "progress_hooks": [self.hook],
                "ffmpeg_location": ffmpeg_dir,
                "windowsfilenames": False,
                "continuedl": True,
                "overwrites": False,
                "retries": 3,
                "fragment_retries": 3,
            }
            plat = detect_platform(self.url) or "other"
            initial_use_cookies = bool(self.use_cookies or (plat != "youtube"))
            apply_session_opts(opts, self.url, use_cookies=initial_use_cookies)

            if self.mode == "video":
                container = self.container
                if container in ("mp4", "mov"):
                    audio_sel = "bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]/bestaudio"
                elif container == "webm":
                    audio_sel = "bestaudio[ext=webm]/bestaudio[acodec^=opus]/bestaudio"
                else:
                    audio_sel = "bestaudio"

                if self.specific_format_id:
                    if self.include_audio:
                        opts["format"] = f"{self.specific_format_id}+{audio_sel}/{self.specific_format_id}+bestaudio/{self.specific_format_id}"
                    else:
                        opts["format"] = f"{self.specific_format_id}"
                else:
                    codec_regex = CODEC_REGEX_MAP.get(self.codec)
                    c_filter = f'[vcodec~="{codec_regex}"]' if codec_regex else ""

                    if self.include_audio:
                        if self.quality == "best":
                            opts["format"] = (
                                f"bestvideo{c_filter}+{audio_sel}/"
                                f"bestvideo{c_filter}+bestaudio/"
                                f"bestvideo{c_filter}/bestvideo+{audio_sel}/best"
                            )
                        elif self.quality == "hd":
                            opts["format"] = (
                                f"bestvideo[format_id*=hd]{c_filter}+{audio_sel}/"
                                f"bestvideo[height>=720]{c_filter}+{audio_sel}/"
                                f"bestvideo{c_filter}+{audio_sel}/"
                                f"bestvideo[format_id*=hd]+{audio_sel}/bestvideo[height>=720]+{audio_sel}/best"
                            )
                        elif self.quality == "sd":
                            opts["format"] = (
                                f"bestvideo[format_id*=sd]{c_filter}+{audio_sel}/"
                                f"bestvideo[height<720]{c_filter}+{audio_sel}/"
                                f"bestvideo{c_filter}+{audio_sel}/"
                                f"bestvideo[format_id*=sd]+{audio_sel}/bestvideo[height<720]+{audio_sel}/best"
                            )
                        else:
                            try:
                                height = int(self.quality)
                                opts["format"] = (
                                    f"bestvideo[height<={height}]{c_filter}+{audio_sel}/"
                                    f"bestvideo{c_filter}+{audio_sel}/"
                                    f"bestvideo[height<={height}]+{audio_sel}/"
                                    f"bestvideo+{audio_sel}/best"
                                )
                            except ValueError:
                                opts["format"] = f"bestvideo{c_filter}+{audio_sel}/bestvideo+{audio_sel}/best"
                    else:
                        # WITHOUT AUDIO: Pure video stream only
                        if self.quality == "best":
                            opts["format"] = f"bestvideo{c_filter}/bestvideo/best"
                        elif self.quality == "hd":
                            opts["format"] = f"bestvideo[format_id*=hd]{c_filter}/bestvideo[height>=720]{c_filter}/bestvideo{c_filter}/best"
                        elif self.quality == "sd":
                            opts["format"] = f"bestvideo[format_id*=sd]{c_filter}/bestvideo[height<720]{c_filter}/bestvideo{c_filter}/best"
                        else:
                            try:
                                height = int(self.quality)
                                opts["format"] = f"bestvideo[height<={height}]{c_filter}/bestvideo{c_filter}/best"
                            except ValueError:
                                opts["format"] = f"bestvideo{c_filter}/bestvideo/best"

                opts["merge_output_format"] = container
                opts["postprocessors"] = [{
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": container,
                }]
            else:
                opts["format"] = "bestaudio/best"
                fmt_upper = self.audio_format.upper()
                if "MP3" in fmt_upper:
                    opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": str(self.audio_bitrate),
                    }]
                elif "M4A" in fmt_upper:
                    opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "m4a",
                    }]
                elif "WAV" in fmt_upper:
                    opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "wav",
                    }]
                elif "FLAC" in fmt_upper:
                    opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "flac",
                    }]
                elif "AAC" in fmt_upper:
                    opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "aac",
                    }]
                elif "OPUS" in fmt_upper:
                    opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "opus",
                    }]
                elif "OGG" in fmt_upper:
                    opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "vorbis",
                    }]
                else:
                    opts["postprocessors"] = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "best",
                    }]

            try:
                with get_ytdlp().YoutubeDL(opts) as ydl:
                    ydl.download([self.url])
            except Exception as dl_err:
                err_str = str(dl_err).lower()
                if not initial_use_cookies and not self._cancel_requested and (
                    "not available" in err_str or "429" in err_str or "sign in" in err_str or "bot" in err_str or "login" in err_str
                ):
                    apply_session_opts(opts, self.url, use_cookies=True)
                    with get_ytdlp().YoutubeDL(opts) as ydl:
                        ydl.download([self.url])
                else:
                    raise dl_err

            # Guarantee QuickTime Player audio compatibility on macOS:
            # If the merged MP4 or MOV file ended up with Opus or Vorbis audio, convert audio to AAC
            if self.mode == "video" and self.include_audio and self.container in ("mp4", "mov") and not self._cancel_requested:
                target_file = None
                expected_ext = f".{self.container}"
                for candidate in (chosen_path, chosen_path.with_suffix(expected_ext)):
                    if candidate.exists() and candidate.is_file():
                        target_file = candidate
                        break
                if not target_file and chosen_path.parent.exists():
                    stem = chosen_path.stem
                    for f in chosen_path.parent.glob(f"{stem}*{expected_ext}"):
                        target_file = f
                        break

                if target_file and ffmpeg_dir:
                    ffmpeg_bin = str(Path(ffmpeg_dir) / "ffmpeg")
                    ffprobe_bin = str(Path(ffmpeg_dir) / "ffprobe") if (Path(ffmpeg_dir) / "ffprobe").exists() else shutil.which("ffprobe")
                    is_opus = False
                    if ffprobe_bin:
                        try:
                            probe = subprocess.run(
                                [ffprobe_bin, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", str(target_file)],
                                capture_output=True, text=True, timeout=5
                            )
                            codec_out = probe.stdout.lower()
                            if "opus" in codec_out or "vorbis" in codec_out:
                                is_opus = True
                        except Exception:
                            pass

                    if is_opus:
                        temp_fixed = target_file.with_name(f"fixed_{target_file.name}")
                        try:
                            subprocess.run(
                                [ffmpeg_bin, "-y", "-i", str(target_file), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(temp_fixed)],
                                capture_output=True, timeout=30
                            )
                            if temp_fixed.exists() and temp_fixed.stat().st_size > 0:
                                temp_fixed.replace(target_file)
                        except Exception:
                            if temp_fixed.exists():
                                temp_fixed.unlink(missing_ok=True)

            if self._cancel_requested:
                self.cancelled.emit()
            else:
                self.completed.emit(str(Path(self.output_path).expanduser().resolve().parent))
        except Exception as e:
            if self._cancel_requested or "CLIPHARBOR_CANCELLED" in str(e):
                self.cancelled.emit()
            else:
                self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(500, 460)
        self.resize(880, 780)
        self.info = None
        self.raw_formats = []
        self.inspect_worker = None
        self.download_worker = None
        self.save_path = None
        self.mode = "video"
        self.current_platform = "auto"
        self.platform_buttons = {}
        self.inspected_all_codecs = {}
        self.inspected_codecs_by_height = {}
        self.media_has_audio = True

        self.settings = QSettings("Remon", "RemonYTDownloader")
        saved_dir = self.settings.value("last_directory", "")
        if saved_dir and Path(str(saved_dir)).is_dir():
            self.last_directory = Path(str(saved_dir))
        else:
            self.last_directory = Path.home() / "Downloads"

        icon_path = resource_path("logo", "RYD.png")
        if not icon_path.exists():
            icon_path = resource_path("logo", "RYD.icns")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        central = QWidget()
        scroll_area.setWidget(central)
        self.setCentralWidget(scroll_area)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        # Header bar
        top = QHBoxLayout()
        logo = QLabel()
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(48, 48)
        logo_file = resource_path("logo", "RYD.png")
        if not logo_file.exists():
            logo_file = resource_path("logo", "RYD.icns")
        if logo_file.exists():
            pix = QPixmap(str(logo_file)).scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pix)
        else:
            logo.setText("⬇")

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        subtitle = QLabel("Universal downloader for YouTube, Facebook, Instagram, TikTok & web media.")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)

        top.addWidget(logo)
        top.addLayout(title_stack, 1)

        self.status_label = QLabel("READY")
        self.status_label.setObjectName("statusPill")
        top.addWidget(self.status_label, 0, Qt.AlignTop)
        root.addLayout(top)

        # Section 01: Platform and URL input card
        url_card = QFrame()
        url_card.setObjectName("card")
        url_layout = QVBoxLayout(url_card)
        url_layout.setContentsMargins(18, 16, 18, 16)
        url_layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.addWidget(self._section_label("01  /  SELECT PLATFORM & MEDIA URL"))
        header_row.addStretch(1)

        self.detected_label = QLabel("")
        self.detected_label.setObjectName("detectedLabel")
        self.detected_label.setVisible(False)
        header_row.addWidget(self.detected_label)
        url_layout.addLayout(header_row)

        # Platform selector buttons in a responsive grid
        self.plat_grid = QGridLayout()
        self.plat_grid.setSpacing(6)
        platforms = [
            ("auto", "✦  Auto Detect"),
            ("youtube", "▶  YouTube"),
            ("facebook", "f  Facebook"),
            ("instagram", "📷  Instagram"),
            ("tiktok", "🎵  TikTok"),
        ]
        for key, label in platforms:
            btn = QPushButton(label)
            btn.setObjectName(f"platBtn_{key}")
            btn.setProperty("platformKey", key)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda checked=False, k=key: self._select_platform(k))
            self.platform_buttons[key] = btn
        url_layout.addLayout(self.plat_grid)

        # URL Input and Inspect Button
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(PLATFORMS["auto"]["placeholder"])
        self.url_input.textChanged.connect(self._url_text_changed)
        self.url_input.returnPressed.connect(self.inspect_video)

        self.inspect_button = QPushButton("Inspect media")
        self.inspect_button.setObjectName("primary")
        self.inspect_button.setCursor(Qt.PointingHandCursor)
        self.inspect_button.clicked.connect(self.inspect_video)

        input_row.addWidget(self.url_input, 1)
        input_row.addWidget(self.inspect_button)
        url_layout.addLayout(input_row)

        hint = QLabel("Supports: YouTube (Videos, Shorts, 4K) • Facebook (Videos, Reels) • Instagram (Reels, Posts) • TikTok (Videos, Sound)")
        hint.setObjectName("tinyHint")
        hint.setWordWrap(True)
        url_layout.addWidget(hint)

        root.addWidget(url_card)

        # Media details card
        self.info_card = QFrame()
        self.info_card.setObjectName("card")
        info_layout = QVBoxLayout(self.info_card)
        info_layout.setContentsMargins(18, 16, 18, 16)
        info_layout.setSpacing(8)

        details_header = QHBoxLayout()
        details_header.addWidget(self._section_label("MEDIA DETAILS"))
        details_header.addStretch(1)

        self.media_platform_badge = QLabel("")
        self.media_platform_badge.setObjectName("platformBadge")
        self.media_platform_badge.setVisible(False)
        details_header.addWidget(self.media_platform_badge)
        info_layout.addLayout(details_header)

        self.video_title = QLabel("Your media details will appear here")
        self.video_title.setObjectName("videoTitle")
        self.video_title.setWordWrap(True)

        self.video_meta = QLabel("Paste a link above, then click Inspect media.")
        self.video_meta.setObjectName("muted")
        self.video_meta.setWordWrap(True)

        info_layout.addWidget(self.video_title)
        info_layout.addWidget(self.video_meta)
        root.addWidget(self.info_card)

        # Section 02: What do you want? (Video vs Audio)
        mode_card = QFrame()
        mode_card.setObjectName("card")
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.setContentsMargins(18, 16, 18, 16)
        mode_layout.setSpacing(12)
        mode_layout.addWidget(self._section_label("02  /  FORMAT & AUDIO OPTIONS"))

        mode_row = QHBoxLayout()
        mode_row.setSpacing(16)
        self.video_radio = QRadioButton("🎬  Video")
        self.audio_radio = QRadioButton("🎵  Audio Only")
        self.video_radio.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.audio_radio.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.video_radio.setChecked(True)
        self.video_radio.setCursor(Qt.PointingHandCursor)
        self.audio_radio.setCursor(Qt.PointingHandCursor)

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.video_radio)
        self.mode_group.addButton(self.audio_radio)
        self.video_radio.toggled.connect(self._mode_changed)
        self.audio_radio.toggled.connect(self._mode_changed)
        mode_row.addWidget(self.video_radio)
        mode_row.addWidget(self.audio_radio)
        mode_row.addStretch(1)
        mode_layout.addLayout(mode_row)

        # Video page
        self.video_page = QWidget()
        video_layout = QVBoxLayout(self.video_page)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(10)

        # Responsive grid for Quality, Container, Codec, Audio Track
        self.video_grid = QGridLayout()
        self.video_grid.setSpacing(10)

        # (0, 0) Resolution / Quality
        self.video_opt_res = QWidget()
        res_col = QVBoxLayout(self.video_opt_res)
        res_col.setContentsMargins(0, 0, 0, 0)
        res_col.setSpacing(4)
        res_col.addWidget(self._field_label("Video resolution / quality"))
        self.video_quality = QComboBox()
        self.video_quality.setCursor(Qt.PointingHandCursor)
        self.video_quality.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.video_quality.setMinimumContentsLength(6)
        self.video_quality.addItem("Best available", "best")
        for h, label in (
            (2160, "2160p (4K UHD)"),
            (1440, "1440p (2K QHD)"),
            (1080, "1080p (Full HD)"),
            (720, "720p (HD)"),
            (480, "480p (SD)"),
            (360, "360p"),
            (240, "240p"),
            (144, "144p"),
        ):
            self.video_quality.addItem(label, str(h))
        self.video_quality.currentIndexChanged.connect(self._on_video_quality_changed)
        res_col.addWidget(self.video_quality)

        # (0, 1) Video format / container
        self.video_opt_container = QWidget()
        container_col = QVBoxLayout(self.video_opt_container)
        container_col.setContentsMargins(0, 0, 0, 0)
        container_col.setSpacing(4)
        container_col.addWidget(self._field_label("Video format (Container)"))
        self.video_container = QComboBox()
        self.video_container.setCursor(Qt.PointingHandCursor)
        self.video_container.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.video_container.setMinimumContentsLength(6)
        self.video_container.addItem("MP4 (.mp4 - Recommended, Universal)", "mp4")
        self.video_container.addItem("MKV (.mkv - Supports all codecs)", "mkv")
        self.video_container.addItem("WEBM (.webm - Modern open web)", "webm")
        self.video_container.addItem("MOV (.mov - Apple QuickTime)", "mov")
        self.video_container.currentIndexChanged.connect(self._on_video_container_changed)
        container_col.addWidget(self.video_container)

        # (1, 0) Video Codec
        self.video_opt_codec = QWidget()
        codec_col = QVBoxLayout(self.video_opt_codec)
        codec_col.setContentsMargins(0, 0, 0, 0)
        codec_col.setSpacing(4)
        codec_col.addWidget(self._field_label("Video codec"))
        self.video_codec = QComboBox()
        self.video_codec.setCursor(Qt.PointingHandCursor)
        self.video_codec.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.video_codec.setMinimumContentsLength(6)
        self.video_codec.addItem("Best available codec (Auto)", "best")
        self.video_codec.addItem("H.264 / AVC (Most compatible)", "h264")
        self.video_codec.addItem("VP9 (High efficiency)", "vp9")
        self.video_codec.addItem("AV1 (Next-generation)", "av1")
        self.video_codec.addItem("H.265 / HEVC", "hevc")
        self.video_codec.currentIndexChanged.connect(self._on_video_codec_changed)
        codec_col.addWidget(self.video_codec)

        # (1, 1) Audio track (With Audio vs Without Audio)
        self.video_opt_audio = QWidget()
        audio_col = QVBoxLayout(self.video_opt_audio)
        audio_col.setContentsMargins(0, 0, 0, 0)
        audio_col.setSpacing(4)
        audio_col.addWidget(self._field_label("Audio track"))
        self.video_audio_track = QComboBox()
        self.video_audio_track.setCursor(Qt.PointingHandCursor)
        self.video_audio_track.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.video_audio_track.setMinimumContentsLength(6)
        self.video_audio_track.addItem("🔊  With Audio (Merged sound)", True)
        self.video_audio_track.addItem("🔇  Without Audio (Video only / Mute)", False)
        self.video_audio_track.currentIndexChanged.connect(self._on_video_audio_changed)
        audio_col.addWidget(self.video_audio_track)

        video_layout.addLayout(self.video_grid)

        # Advanced Stream Selector Toggle (Shows all raw streams & formats)
        self.specific_stream_toggle = QCheckBox("⚡  Pick specific stream (Show all raw formats, codecs & bitrates)")
        self.specific_stream_toggle.setCursor(Qt.PointingHandCursor)
        self.specific_stream_toggle.toggled.connect(self._toggle_specific_stream)
        video_layout.addWidget(self.specific_stream_toggle)

        self.specific_stream_container = QWidget()
        specific_layout = QVBoxLayout(self.specific_stream_container)
        specific_layout.setContentsMargins(0, 2, 0, 0)
        specific_layout.setSpacing(4)
        self.specific_stream_combo = QComboBox()
        self.specific_stream_combo.setCursor(Qt.PointingHandCursor)
        self.specific_stream_combo.addItem("Auto / Use settings above (Recommended)", "")
        self.specific_stream_combo.currentIndexChanged.connect(self._on_specific_stream_changed)
        specific_layout.addWidget(self.specific_stream_combo)
        self.specific_stream_container.setVisible(False)
        video_layout.addWidget(self.specific_stream_container)

        self.video_selection_hint = QLabel("")
        self.video_selection_hint.setObjectName("tinyHint")
        self.video_selection_hint.setWordWrap(True)
        video_layout.addWidget(self.video_selection_hint)
        self._update_video_selection_hint()

        # Audio format page
        self.audio_page = QWidget()
        audio_layout = QVBoxLayout(self.audio_page)
        audio_layout.setContentsMargins(0, 0, 0, 0)
        audio_layout.setSpacing(10)

        self.audio_grid = QGridLayout()
        self.audio_grid.setSpacing(10)

        self.audio_opt_format = QWidget()
        afmt_col = QVBoxLayout(self.audio_opt_format)
        afmt_col.setContentsMargins(0, 0, 0, 0)
        afmt_col.setSpacing(4)
        afmt_col.addWidget(self._field_label("Audio format"))
        self.audio_format = QComboBox()
        self.audio_format.setCursor(Qt.PointingHandCursor)
        self.audio_format.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.audio_format.setMinimumContentsLength(6)
        self.audio_format.addItems([
            "MP3 (.mp3 - Universal)",
            "M4A (.m4a - Apple AAC)",
            "WAV (.wav - Lossless uncompressed)",
            "FLAC (.flac - Lossless studio quality)",
            "AAC (.aac - Advanced Audio Coding)",
            "OPUS (.opus - High efficiency)",
            "OGG (.ogg - Vorbis audio)",
            "Original (Best available stream)",
        ])
        self.audio_format.currentTextChanged.connect(self._audio_format_changed)
        afmt_col.addWidget(self.audio_format)

        self.audio_opt_bitrate = QWidget()
        abit_col = QVBoxLayout(self.audio_opt_bitrate)
        abit_col.setContentsMargins(0, 0, 0, 0)
        abit_col.setSpacing(4)
        self.bitrate_label = self._field_label("Audio quality / bitrate")
        abit_col.addWidget(self.bitrate_label)
        self.audio_bitrate = QComboBox()
        self.audio_bitrate.setCursor(Qt.PointingHandCursor)
        self.audio_bitrate.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.audio_bitrate.setMinimumContentsLength(6)
        self.audio_bitrate.addItems(["320 kbps (Highest quality)", "256 kbps", "192 kbps (Standard)", "128 kbps"])
        abit_col.addWidget(self.audio_bitrate)

        audio_layout.addLayout(self.audio_grid)

        mode_layout.addWidget(self.video_page)
        mode_layout.addWidget(self.audio_page)
        self.video_page.setVisible(True)
        self.audio_page.setVisible(False)
        root.addWidget(mode_card)

        # Section 03: Download & Progress card
        progress_card = QFrame()
        progress_card.setObjectName("card")
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(18, 16, 18, 16)
        progress_layout.setSpacing(10)
        progress_layout.addWidget(self._section_label("03  /  DOWNLOAD & PROGRESS"))

        self.location_label = QLabel(f"📁 Default folder: {self.last_directory} (Media name will be used automatically)")
        self.location_label.setObjectName("locationLabel")
        self.location_label.setWordWrap(True)

        self.progress_label = QLabel("Paste and inspect a media link above to begin.")
        self.progress_label.setObjectName("muted")
        self.progress_label.setWordWrap(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.choose_location_button = QPushButton("Choose location")
        self.choose_location_button.setCursor(Qt.PointingHandCursor)
        self.choose_location_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.choose_location_button.clicked.connect(self.choose_location)

        self.start_button = QPushButton("Start Download")
        self.start_button.setObjectName("primary")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_download)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_download)

        buttons.addWidget(self.choose_location_button, 2)
        buttons.addWidget(self.start_button, 3)
        buttons.addWidget(self.cancel_button, 1)

        progress_layout.addWidget(self.location_label)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addLayout(buttons)
        root.addWidget(progress_card)

        footer = QLabel("Remon YT Downloader • YouTube • Facebook • Instagram • TikTok • Direct Downloads")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignCenter)
        footer.setWordWrap(True)
        root.addWidget(footer)

        self._select_platform("auto")
        self._audio_format_changed(self.audio_format.currentText())
        self._reflow_responsive_layout(self.width())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow_responsive_layout(self.width())

    def _reflow_responsive_layout(self, width):
        is_narrow = (width < 620)
        if getattr(self, "_last_reflow_narrow", None) == is_narrow:
            return
        self._last_reflow_narrow = is_narrow

        # Reflow platform buttons
        if hasattr(self, "plat_grid") and self.platform_buttons:
            while self.plat_grid.count():
                self.plat_grid.takeAt(0)
            if is_narrow:
                self.plat_grid.addWidget(self.platform_buttons["auto"], 0, 0, 1, 2)
                self.plat_grid.addWidget(self.platform_buttons["youtube"], 0, 2, 1, 2)
                self.plat_grid.addWidget(self.platform_buttons["facebook"], 1, 0)
                self.plat_grid.addWidget(self.platform_buttons["instagram"], 1, 1, 1, 2)
                self.plat_grid.addWidget(self.platform_buttons["tiktok"], 1, 3)
            else:
                for idx, key in enumerate(["auto", "youtube", "facebook", "instagram", "tiktok"]):
                    if key in self.platform_buttons:
                        self.plat_grid.addWidget(self.platform_buttons[key], 0, idx)

        # Reflow video options
        if hasattr(self, "video_grid") and hasattr(self, "video_opt_res"):
            while self.video_grid.count():
                self.video_grid.takeAt(0)
            if is_narrow:
                self.video_grid.addWidget(self.video_opt_res, 0, 0)
                self.video_grid.addWidget(self.video_opt_container, 1, 0)
                self.video_grid.addWidget(self.video_opt_codec, 2, 0)
                self.video_grid.addWidget(self.video_opt_audio, 3, 0)
            else:
                self.video_grid.addWidget(self.video_opt_res, 0, 0)
                self.video_grid.addWidget(self.video_opt_container, 0, 1)
                self.video_grid.addWidget(self.video_opt_codec, 1, 0)
                self.video_grid.addWidget(self.video_opt_audio, 1, 1)

        # Reflow audio options
        if hasattr(self, "audio_grid") and hasattr(self, "audio_opt_format"):
            while self.audio_grid.count():
                self.audio_grid.takeAt(0)
            if is_narrow:
                self.audio_grid.addWidget(self.audio_opt_format, 0, 0)
                self.audio_grid.addWidget(self.audio_opt_bitrate, 1, 0)
            else:
                self.audio_grid.addWidget(self.audio_opt_format, 0, 0)
                self.audio_grid.addWidget(self.audio_opt_bitrate, 0, 1)

    def _section_label(self, text):
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def _field_label(self, text):
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _select_platform(self, key):
        self.current_platform = key
        for k, btn in self.platform_buttons.items():
            btn.setProperty("active", k == key)
            self._update_button_style(btn, k, k == key)

        pinfo = PLATFORMS.get(key, PLATFORMS["auto"])
        self.url_input.setPlaceholderText(pinfo["placeholder"])

        url = self.url_input.text().strip()
        if url:
            self._url_text_changed(url)

    def _update_button_style(self, btn, key, is_active):
        pinfo = PLATFORMS.get(key, PLATFORMS["auto"])
        if is_active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {pinfo['bg']};
                    color: #FFFFFF;
                    border: 1.5px solid {pinfo['color']};
                    border-radius: 9px;
                    padding: 8px 10px;
                    font-size: 12px;
                    font-weight: 750;
                }}
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background: #181A22;
                    color: #A3A8BD;
                    border: 1px solid #2B2E3D;
                    border-radius: 9px;
                    padding: 8px 10px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #232634;
                    color: #FFFFFF;
                    border-color: #3E4359;
                }
            """)

    def _url_text_changed(self, text):
        url = text.strip()
        plat = detect_platform(url)
        if plat and plat in PLATFORMS and plat != "other":
            pinfo = PLATFORMS[plat]
            self.detected_label.setText(f"Detected: {pinfo['icon']} {pinfo['name']}")
            self.detected_label.setStyleSheet(f"color: {pinfo['color']}; font-size: 11px; font-weight: 700; padding: 2px 6px; background: {pinfo['bg']}; border-radius: 6px; border: 1px solid {pinfo['border']};")
            self.detected_label.setVisible(True)
        elif url:
            self.detected_label.setText("Detected: 🌐 Web Media")
            self.detected_label.setStyleSheet("color: #9A9EAF; font-size: 11px; font-weight: 600; padding: 2px 6px; background: #20232D; border-radius: 6px; border: 1px solid #38344F;")
            self.detected_label.setVisible(True)
        else:
            self.detected_label.setVisible(False)

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #101116;
                color: #F2F3F8;
                font-size: 13px;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background: #101116;
                width: 10px;
                margin: 4px 2px 4px 2px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #2D303E;
                min-height: 25px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #8B7CFF;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background: #101116;
                height: 10px;
                margin: 2px 4px 2px 4px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #2D303E;
                min-width: 25px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #8B7CFF;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QFrame#card {
                background: #191B23;
                border: 1px solid #2A2D39;
                border-radius: 16px;
            }
            QLabel#logo {
                background: #8B7CFF;
                color: #11121A;
                border-radius: 14px;
                font-size: 26px;
                font-weight: 800;
            }
            QLabel#appTitle {
                font-size: 22px;
                font-weight: 750;
                color: #FAFAFF;
            }
            QLabel#muted, QLabel#footer {
                color: #9A9EAF;
            }
            QLabel#footer {
                font-size: 11px;
                padding: 4px 0;
            }
            QLabel#tinyHint {
                color: #8E93AA;
                font-size: 11px;
                padding-top: 2px;
            }
            QLabel#locationLabel {
                color: #8B7CFF;
                font-size: 12px;
                font-weight: 600;
                padding: 2px 0;
            }
            QLabel#statusPill {
                background: #20232D;
                color: #B6AEFF;
                border: 1px solid #38344F;
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 1px;
            }
            QLabel#sectionLabel {
                color: #A6A9BB;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 1.3px;
            }
            QLabel#videoTitle {
                color: #F8F8FC;
                font-size: 15px;
                font-weight: 650;
            }
            QLabel#fieldLabel {
                color: #D8DAE5;
                font-size: 12px;
                font-weight: 600;
                padding-top: 1px;
            }
            QLineEdit, QComboBox {
                background: #101218;
                border: 1px solid #353846;
                border-radius: 10px;
                padding: 10px 12px;
                color: #F4F4FA;
                selection-background-color: #6E61D9;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #8B7CFF;
            }
            QComboBox::drop-down {
                border: 0;
                width: 26px;
            }
            QComboBox QAbstractItemView {
                background: #1C1E27;
                color: #F4F4FA;
                selection-background-color: #6E61D9;
                selection-color: #FFFFFF;
                border: 1px solid #383B49;
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 28px;
                padding: 4px 8px;
            }
            QPushButton {
                background: #292C37;
                color: #F0F1F8;
                border: 1px solid #393C49;
                border-radius: 10px;
                padding: 10px 16px;
                font-weight: 650;
            }
            QPushButton:hover {
                background: #353846;
            }
            QPushButton:disabled {
                color: #686C7B;
                background: #20222A;
                border-color: #2A2C35;
            }
            QPushButton#primary {
                background: #8B7CFF;
                color: #101116;
                border: 0;
                font-weight: 800;
            }
            QPushButton#primary:hover {
                background: #A197FF;
            }
            QRadioButton {
                spacing: 8px;
                color: #E7E8F0;
                font-weight: 650;
                padding: 4px 6px;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #5B5F70;
                background: #141721;
                border-radius: 8px;
            }
            QRadioButton::indicator:checked {
                border: 4px solid #8B7CFF;
                background: #FFFFFF;
                border-radius: 8px;
            }
            QCheckBox {
                spacing: 8px;
                color: #B4B9CE;
                font-weight: 600;
                font-size: 12px;
                padding: 4px 0;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #484C60;
                border-radius: 4px;
                background: #12141B;
            }
            QCheckBox::indicator:checked {
                border-color: #8B7CFF;
                background: #8B7CFF;
            }
            QProgressBar {
                background: #101218;
                border: 1px solid #343745;
                border-radius: 7px;
                height: 14px;
                text-align: center;
                color: #E8E6FF;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background: #8B7CFF;
                border-radius: 6px;
            }
        """)

    def _get_video_extension(self):
        container = (self.video_container.currentData() or "mp4").lower()
        return f".{container}"

    def _get_audio_extension(self):
        fmt = self.audio_format.currentText().upper()
        if "MP3" in fmt:
            return ".mp3"
        elif "M4A" in fmt:
            return ".m4a"
        elif "WAV" in fmt:
            return ".wav"
        elif "FLAC" in fmt:
            return ".flac"
        elif "AAC" in fmt:
            return ".aac"
        elif "OPUS" in fmt:
            return ".opus"
        elif "OGG" in fmt:
            return ".ogg"
        return ".m4a"

    def _clean_media_title(self):
        if not self.info or not self.info.get("title"):
            plat = detect_platform(self.url_input.text().strip()) or self.current_platform or "Media"
            plat_name = PLATFORMS.get(plat, {}).get("name", "Media")
            return f"{plat_name} Download"
        raw = self.info.get("title", "")
        clean = re.sub(r'[/\\:*?"<>|]', "-", raw).strip()
        clean = re.sub(r'\s+', ' ', clean)[:120].strip()
        return clean or "Media Download"

    def _update_save_path_display(self):
        ext = self._get_video_extension() if self.mode == "video" else self._get_audio_extension()
        clean_title = self._clean_media_title()
        if self.save_path:
            self.save_path = str(Path(self.save_path).with_suffix(ext))
        else:
            self.save_path = str(self.last_directory / f"{clean_title}{ext}")

        filename = Path(self.save_path).name
        folder = Path(self.save_path).parent
        self.location_label.setText(f"📁 Save location: {filename} in {folder}")
        if self.info and self.info.get("title"):
            self.start_button.setEnabled(True)

    def _mode_changed(self, *args):
        self.mode = "video" if self.video_radio.isChecked() else "audio"
        self.video_page.setVisible(self.mode == "video")
        self.audio_page.setVisible(self.mode == "audio")
        self._update_save_path_display()

    def _audio_format_changed(self, value):
        val = value.upper()
        is_bitrate_applicable = ("MP3" in val or "AAC" in val or "M4A" in val)
        self.audio_opt_bitrate.setVisible(is_bitrate_applicable)
        if self.mode == "audio":
            self._update_save_path_display()

    def _on_video_quality_changed(self, *args):
        self._update_video_codec_options()
        self._update_video_selection_hint()

    def _on_video_container_changed(self, *args):
        self._update_save_path_display()
        self._update_video_selection_hint()

    def _on_video_codec_changed(self, *args):
        self._update_video_selection_hint()

    def _on_video_audio_changed(self, *args):
        self._update_video_selection_hint()

    def _toggle_specific_stream(self, checked):
        self.specific_stream_container.setVisible(checked)
        self._update_video_selection_hint()

    def _on_specific_stream_changed(self, *args):
        self._update_video_selection_hint()

    def _update_video_codec_options(self):
        prev_codec = self.video_codec.currentData() or "best"
        self.video_codec.blockSignals(True)
        self.video_codec.clear()

        selected_res = self.video_quality.currentData() or "best"
        if selected_res == "best":
            self.video_codec.addItem("Best available codec (Auto)", "best")
        elif selected_res in ("hd", "sd"):
            self.video_codec.addItem(f"Best available for {selected_res.upper()}", "best")
        else:
            self.video_codec.addItem(f"Best available for {selected_res}p", "best")

        if self.inspected_all_codecs:
            sort_order = {"h264": 1, "vp9": 2, "av1": 3, "hevc": 4, "mp4v": 5}
            sorted_codecs = sorted(
                self.inspected_all_codecs.items(),
                key=lambda item: (sort_order.get(item[0], 99), item[0])
            )

            try:
                selected_height = int(selected_res)
            except (ValueError, TypeError):
                selected_height = None

            for ckey, cinfo in sorted_codecs:
                cname = cinfo["name"]
                heights = cinfo["heights"]
                max_h = max(heights) if heights else None

                if selected_height is not None:
                    if selected_height in heights:
                        status_desc = f"Available at {selected_height}p"
                    elif max_h:
                        status_desc = f"Max {max_h}p available"
                    else:
                        status_desc = "Available"
                else:
                    if max_h:
                        status_desc = f"Up to {max_h}p"
                    else:
                        status_desc = "Available"

                label = f"{cname} ({status_desc})"
                self.video_codec.addItem(label, ckey)
        else:
            self.video_codec.addItem("H.264 / AVC (Most compatible)", "h264")
            self.video_codec.addItem("VP9 (High efficiency)", "vp9")
            self.video_codec.addItem("AV1 (Next-generation)", "av1")
            self.video_codec.addItem("H.265 / HEVC", "hevc")

        found_idx = -1
        for idx in range(self.video_codec.count()):
            if self.video_codec.itemData(idx) == prev_codec:
                found_idx = idx
                break
        if found_idx >= 0:
            self.video_codec.setCurrentIndex(found_idx)
        else:
            self.video_codec.setCurrentIndex(0)

        self.video_codec.blockSignals(False)
        self._update_video_selection_hint()

    def _update_video_selection_hint(self):
        res_data = self.video_quality.currentData() or "best"
        codec_data = self.video_codec.currentData() or "best"
        container = (self.video_container.currentData() or "mp4").upper()
        include_audio = self.video_audio_track.currentData()
        if include_audio is None:
            include_audio = True

        if res_data == "best":
            res_str = "Best available resolution"
        elif res_data == "hd":
            res_str = "HD resolution"
        elif res_data == "sd":
            res_str = "SD resolution"
        else:
            res_str = f"{res_data}p"

        codec_names = {
            "best": "Best available codec",
            "h264": "H.264 / AVC",
            "vp9": "VP9",
            "av1": "AV1",
            "hevc": "H.265 / HEVC",
            "mp4v": "MPEG-4",
        }
        codec_str = codec_names.get(codec_data, codec_data.upper())

        has_audio = getattr(self, "media_has_audio", True)
        if not has_audio:
            audio_hint = " • 🔇 Warning: Source has no audio track"
        elif include_audio:
            audio_hint = " • 🔊 With audio (Sound included)"
        else:
            audio_hint = " • 🔇 Without audio (Video only / Mute)"

        stream_id = self.specific_stream_combo.currentData() if hasattr(self, "specific_stream_combo") and self.specific_stream_toggle.isChecked() else None
        stream_note = f" • Stream #{stream_id}" if stream_id else ""

        self.video_selection_hint.setText(f"Target: {res_str} • {container} • {codec_str}{audio_hint}{stream_note}")
        self.video_selection_hint.setVisible(True)

    def inspect_video(self):
        url = self.url_input.text().strip()
        if not is_valid_url(url, self.current_platform):
            plat_name = PLATFORMS.get(self.current_platform, {}).get("name", "supported")
            QMessageBox.warning(self, "Check the link", f"Paste a valid {plat_name} media URL first.")
            return

        self.inspect_button.setEnabled(False)
        self.status_label.setText("INSPECTING")
        self.progress_label.setText("Discovering all resolutions, formats, and codecs…")
        self.inspect_worker = InspectWorker(url)
        self.inspect_worker.finished_info.connect(self._inspection_succeeded)
        self.inspect_worker.failed.connect(self._inspection_failed)
        self.inspect_worker.finished.connect(lambda: self.inspect_button.setEnabled(True))
        self.inspect_worker.start()

    def _inspection_succeeded(self, info):
        self.info = info
        self.video_title.setText(info["title"])

        plat_key = info.get("platform") or detect_platform(self.url_input.text().strip()) or "other"
        plat_meta = PLATFORMS.get(plat_key, {
            "name": plat_key.title(),
            "icon": "🌐",
            "color": "#8B7CFF",
            "bg": "#222038",
            "border": "#4C4477",
        })

        self.media_platform_badge.setText(f"{plat_meta['icon']}  {plat_meta['name'].upper()}")
        self.media_platform_badge.setStyleSheet(f"""
            background: {plat_meta['bg']};
            color: {plat_meta['color']};
            border: 1px solid {plat_meta['border']};
            border-radius: 8px;
            padding: 4px 9px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
        """)
        self.media_platform_badge.setVisible(True)

        has_audio = info.get("has_audio", True)
        self.media_has_audio = has_audio

        meta_parts = []
        if info.get("uploader"):
            meta_parts.append(f"Uploader: {info['uploader']}")
        if info.get("duration"):
            meta_parts.append(f"Duration: {info['duration']}")
        meta_parts.append(f"{len(info.get('formats', []))} format streams detected")
        if has_audio:
            meta_parts.append("🔊 Audio available")
        else:
            meta_parts.append("🔇 Silent video (No audio track in source)")
        self.video_meta.setText("   •   ".join(meta_parts))

        self.status_label.setText("LINK READY")
        self.progress_label.setText("Choose resolution, container, codec and audio options, then click Start Download.")

        raw_formats = info.get("formats", [])
        self.raw_formats = raw_formats

        # Extract codecs and heights
        codecs_by_height = {}
        all_codecs = {}
        height_filesizes = {}

        for f in raw_formats:
            vc = f.get("vcodec")
            h = f.get("height")
            ckey, cname = classify_vcodec(vc)
            if ckey and ckey not in all_codecs:
                all_codecs[ckey] = {
                    "name": cname,
                    "heights": set(),
                }
            if h:
                if ckey:
                    all_codecs[ckey]["heights"].add(h)
                    if h not in codecs_by_height:
                        codecs_by_height[h] = set()
                    codecs_by_height[h].add(cname)
                fs = f.get("filesize")
                if fs and (h not in height_filesizes or fs > height_filesizes[h]):
                    height_filesizes[h] = fs

        self.inspected_all_codecs = all_codecs
        self.inspected_codecs_by_height = codecs_by_height

        heights = sorted({f["height"] for f in raw_formats if f.get("height") and f.get("vcodec") != "none"}, reverse=True)

        self.video_quality.blockSignals(True)
        self.video_quality.clear()
        self.video_quality.addItem("Best available (Highest quality)", "best")

        if info.get("has_hd"):
            self.video_quality.addItem("HD (High Definition)", "hd")
        if info.get("has_sd"):
            self.video_quality.addItem("SD (Standard Definition)", "sd")

        for h in heights:
            c_list = sorted(codecs_by_height.get(h, []))
            c_tag = f" • [{', '.join(c_list)}]" if c_list else ""
            size_str = f" • ~{format_bytes(height_filesizes[h])}" if h in height_filesizes else ""
            if h == 2160:
                name = f"2160p (4K UHD){c_tag}{size_str}"
            elif h == 1440:
                name = f"1440p (2K QHD){c_tag}{size_str}"
            elif h == 1080:
                name = f"1080p (Full HD){c_tag}{size_str}"
            elif h == 720:
                name = f"720p (HD){c_tag}{size_str}"
            elif h == 480:
                name = f"480p (SD){c_tag}{size_str}"
            elif h == 360:
                name = f"360p{c_tag}{size_str}"
            elif h == 240:
                name = f"240p{c_tag}{size_str}"
            elif h == 144:
                name = f"144p{c_tag}{size_str}"
            else:
                name = f"{h}p{c_tag}{size_str}"
            self.video_quality.addItem(name, str(h))

        if not heights and not info.get("has_hd") and not info.get("has_sd"):
            for h in (2160, 1440, 1080, 720, 480, 360):
                self.video_quality.addItem(f"{h}p or best below", str(h))

        self.video_quality.blockSignals(False)

        # Populate Specific Stream Selector with all raw formats
        self.specific_stream_combo.blockSignals(True)
        self.specific_stream_combo.clear()
        self.specific_stream_combo.addItem("Auto / Use settings above (Recommended)", "")

        playable_formats = []
        for f in raw_formats:
            ext = (f.get("ext") or "").upper()
            if ext == "MHTML" or "storyboard" in (f.get("note") or "").lower():
                continue
            has_vid = f.get("has_video") if "has_video" in f else bool(f.get("vcodec") and f.get("vcodec") != "none")
            has_aud = f.get("has_audio") if "has_audio" in f else bool(f.get("acodec") and f.get("acodec") != "none")
            if not has_vid and not has_aud:
                continue
            f["has_video"] = has_vid
            f["has_audio"] = has_aud
            playable_formats.append(f)

        # Sort: video streams top (height desc, then fps desc), then audio streams (tbr desc)
        playable_formats.sort(
            key=lambda x: (
                1 if x.get("has_video") else 0,
                x.get("height") or 0,
                x.get("fps") or 0,
                x.get("tbr") or x.get("abr") or 0
            ),
            reverse=True
        )

        for f in playable_formats:
            fid = f.get("format_id", "")
            ext = (f.get("ext") or "").upper()
            h = f.get("height")
            res = f.get("resolution") or (f"{h}p" if h else ("Audio only" if not f.get("has_video") else "Video"))
            vcodec_name = classify_vcodec(f.get("vcodec"))[1] or ("Video" if f.get("has_video") else "Audio")
            audio_tag = "🔊 With audio" if f.get("has_audio") else ("🔇 Video only" if f.get("has_video") else "🎵 Audio only")
            fps_tag = f"{int(f['fps'])}fps" if f.get("fps") else ""
            size_tag = format_bytes(f.get("filesize"))
            parts = [f"Stream #{fid}", res, ext, vcodec_name]
            if fps_tag:
                parts.append(fps_tag)
            if size_tag:
                parts.append(size_tag)
            parts.append(audio_tag)
            self.specific_stream_combo.addItem(" • ".join(parts), fid)
        self.specific_stream_combo.blockSignals(False)

        self._update_video_codec_options()
        self._update_save_path_display()
        self.progress_bar.setValue(0)

    def _inspection_failed(self, error):
        self.info = None
        self.raw_formats = []
        self.inspected_all_codecs = {}
        self.inspected_codecs_by_height = {}
        self.media_has_audio = True
        self._update_video_codec_options()
        self.status_label.setText("CHECK FAILED")
        self.progress_label.setText("Could not inspect this link.")
        plat = detect_platform(self.url_input.text().strip())
        QMessageBox.critical(self, "Could not inspect media", self._friendly_error(error, plat))

    def _friendly_error(self, error, platform=None):
        message = str(error)
        plat_name = PLATFORMS.get(platform, {}).get("name", "The platform")
        if "CLIPHARBOR_CANCELLED" in message:
            return "Download was cancelled."
        if "empty media response" in message or "not granting access" in message:
            return (
                f"{plat_name} is restricting anonymous access to this content.\n\n"
                f"Make sure you are logged into {plat_name} in your browser (Chrome, Firefox, Brave, Edge, or Safari) "
                "so ClipHarbor can automatically use your session cookies to access it."
            )
        if "Sign in" in message or "login" in message.lower() or "cookies" in message.lower() or "bot" in message.lower():
            return (
                f"{plat_name} is requiring verification or login for this content.\n\n"
                f"Make sure you are logged into {plat_name} in your browser (Chrome, Firefox, Brave, Edge, or Safari) "
                "so ClipHarbor can use your session."
            )
        if "HTTP Error 429" in message:
            return f"{plat_name} is temporarily rate-limiting requests. Please wait a minute and try again."
        if "HTTP Error 404" in message or "does not exist" in message:
            return f"The media was not found on {plat_name}. Please check that the URL is correct and the post is public."
        return message[:1800]

    def choose_location(self):
        url = self.url_input.text().strip()
        if not is_valid_url(url, self.current_platform):
            plat_name = PLATFORMS.get(self.current_platform, {}).get("name", "supported")
            QMessageBox.warning(self, "Check the link", f"Paste a valid {plat_name} media URL first.")
            return

        clean_title = self._clean_media_title()
        ext = self._get_video_extension() if self.mode == "video" else self._get_audio_extension()
        initial_file = str(self.last_directory / f"{clean_title}{ext}")

        filter_desc = f"{ext.upper()[1:]} files (*{ext});;All media files (*)"
        path, _ = QFileDialog.getSaveFileName(
            self, "Choose download location", initial_file, filter_desc
        )
        if not path:
            return

        self.save_path = path
        self.last_directory = Path(path).parent
        self.settings.setValue("last_directory", str(self.last_directory))
        self.location_label.setText(f"📁 Save location: {Path(path).name} in {self.last_directory}")
        self.progress_label.setText("Location chosen. Click 'Start Download' to begin.")
        self.start_button.setEnabled(True)

    def start_download(self):
        url = self.url_input.text().strip()
        if not is_valid_url(url, self.current_platform):
            plat_name = PLATFORMS.get(self.current_platform, {}).get("name", "supported")
            QMessageBox.warning(self, "Check the link", f"Paste a valid {plat_name} media URL first.")
            return

        if not self.save_path:
            self._update_save_path_display()
            if not self.save_path:
                self.choose_location()
                if not self.save_path:
                    return

        if self.mode == "video":
            quality = self.video_quality.currentData() or "best"
            container = self.video_container.currentData() or "mp4"
            codec = self.video_codec.currentData() or "best"
            include_audio = self.video_audio_track.currentData()
            if include_audio is None:
                include_audio = True

            specific_format_id = None
            if self.specific_stream_toggle.isChecked():
                chosen_fid = self.specific_stream_combo.currentData()
                if chosen_fid:
                    specific_format_id = chosen_fid

            audio_format, bitrate = "Original", "192"
        else:
            quality = "best"
            container = "mp4"
            codec = "best"
            include_audio = True
            specific_format_id = None
            audio_format = self.audio_format.currentText()
            bitrate = self.audio_bitrate.currentText().split()[0]

        output_dir = self.save_path
        self.choose_location_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.inspect_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting download…")
        self.status_label.setText("DOWNLOADING")

        use_cookies = bool(self.info and self.info.get("used_cookies"))
        self.download_worker = DownloadWorker(
            url=url,
            mode=self.mode,
            quality=quality,
            audio_format=audio_format,
            audio_bitrate=bitrate,
            output_path=output_dir,
            codec=codec,
            container=container,
            include_audio=include_audio,
            specific_format_id=specific_format_id,
            use_cookies=use_cookies,
        )
        self.download_worker.progress.connect(self._download_progress)
        self.download_worker.completed.connect(self._download_completed)
        self.download_worker.failed.connect(self._download_failed)
        self.download_worker.cancelled.connect(self._download_cancelled)
        self.download_worker.finished.connect(self._download_thread_finished)
        self.download_worker.start()

    def _download_progress(self, data):
        if data.get("status") == "downloading":
            total = data.get("total") or 0
            downloaded = data.get("downloaded") or 0
            if total:
                self.progress_bar.setValue(max(0, min(100, int(downloaded * 100 / total))))
            speed = data.get("speed")
            eta = data.get("eta")
            details = []
            if speed:
                details.append(f"{speed / 1024 / 1024:.1f} MB/s")
            if eta is not None:
                details.append(f"ETA {int(eta)}s")
            self.progress_label.setText("Downloading… " + (" • ".join(details) if details else "Receiving media data"))
        elif data.get("status") == "finished":
            self.progress_label.setText("Download received; processing or converting container if needed…")
            self.progress_bar.setValue(100)

    def _download_completed(self, folder):
        self.last_directory = Path(folder)
        self.settings.setValue("last_directory", str(self.last_directory))
        self.progress_bar.setValue(100)
        self.status_label.setText("COMPLETE")
        self.progress_label.setText("Finished! Your file is saved in the selected folder.")
        box = QMessageBox(self)
        box.setWindowTitle("Download complete")
        box.setText("Your download is ready.")
        box.setInformativeText(folder)
        open_button = box.addButton("Open folder", QMessageBox.AcceptRole)
        box.addButton("Close", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() == open_button:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _download_failed(self, error):
        self.status_label.setText("DOWNLOAD FAILED")
        self.progress_label.setText("The download did not finish.")
        plat = detect_platform(self.url_input.text().strip())
        QMessageBox.critical(self, "Download failed", self._friendly_error(error, plat))

    def _download_cancelled(self):
        self.status_label.setText("CANCELLED")
        self.progress_label.setText("Download cancelled. Any partial file may remain in the selected folder.")

    def _download_thread_finished(self):
        self.choose_location_button.setEnabled(True)
        self.start_button.setEnabled(bool(self.save_path))
        self.inspect_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def cancel_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.cancel()
            self.cancel_button.setEnabled(False)
            self.progress_label.setText("Cancelling…")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Remon")
    icon_path = resource_path("logo", "RYD.png")
    if not icon_path.exists():
        icon_path = resource_path("logo", "RYD.icns")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setFont(QFont(".AppleSystemUIFont", 13))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
