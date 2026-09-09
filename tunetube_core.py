"""TuneTube download engine.

Shared by the command line entry point (``youtube.py``) and the GUI (``gui.py``).

Nothing in here prints or touches a widget: every entry point takes a ``log``
callback and an optional ``progress`` callback, so the caller decides where the
text ends up. The CLI passes ``print``, the GUI pushes onto a queue that its Tk
loop drains.
"""

from __future__ import annotations

import os
import shutil
import sys

try:
    import yt_dlp
except ImportError:  # kept importable so the GUI can show a friendly message
    yt_dlp = None


class MissingDependency(RuntimeError):
    """yt-dlp is not installed in the running interpreter."""


class Cancelled(Exception):
    """Raised out of the progress hook when the caller asks us to stop."""


# --------------------------------------------------------------------------
# environment
# --------------------------------------------------------------------------

def ytdlp_version():
    """Return the installed yt-dlp version, or None if it is not importable."""
    if yt_dlp is None:
        return None
    return getattr(yt_dlp.version, '__version__', 'unknown')


def ffmpeg_available():
    """FFmpeg is required to merge DASH streams (>1080p) and to make MP3s."""
    return shutil.which('ffmpeg') is not None


def default_download_dir():
    downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
    base = downloads if os.path.isdir(downloads) else os.path.expanduser('~')
    return os.path.join(base, 'TuneTube')


def _require_ytdlp():
    if yt_dlp is None:
        raise MissingDependency(
            'yt-dlp is not installed for this interpreter. '
            'Install it with:  pip install yt-dlp'
        )


# --------------------------------------------------------------------------
# formatting helpers (also used by the GUI for its status line)
# --------------------------------------------------------------------------

def format_bytes(num):
    if not num:
        return '?'
    size = float(num)
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if size < 1024.0 or unit == 'TiB':
            return f'{int(size)} B' if unit == 'B' else f'{size:.1f} {unit}'
        size /= 1024.0


def format_duration(seconds):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return 'unknown'
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f'{hours}:{minutes:02d}:{secs:02d}'
    return f'{minutes}:{secs:02d}'


def format_date(yyyymmdd):
    text = str(yyyymmdd or '')
    if len(text) == 8 and text.isdigit():
        return f'{text[0:4]}-{text[4:6]}-{text[6:8]}'
    return 'unknown'


class _Logger:
    """Adapts yt-dlp's logger interface onto a single ``log(text, level)``."""

    def __init__(self, log):
        self._log = log

    def debug(self, msg):
        # yt-dlp routes ordinary "[download] ..." chatter through debug().
        if msg.startswith('[debug] '):
            return
        self._log(msg, 'dim')

    def info(self, msg):
        self._log(msg, 'info')

    def warning(self, msg):
        self._log(msg, 'warn')

    def error(self, msg):
        self._log(msg, 'error')


def _noop_log(text, level='info'):
    pass


# --------------------------------------------------------------------------
# metadata
# --------------------------------------------------------------------------

def fetch_info(url, log=None):
    """Resolve ``url`` and return yt-dlp's info dict (no download)."""
    _require_ytdlp()
    log = log or _noop_log
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': True,
        'logger': _Logger(log),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # A playlist or profile URL still yields entries; describe the first item.
    if info.get('_type') == 'playlist' and info.get('entries'):
        entries = [entry for entry in info['entries'] if entry]
        if entries:
            log(f'playlist detected ({len(entries)} items) - showing the first entry',
                'warn')
            info = entries[0]
    return info


def describe(info):
    """Return ``[(text, level)]`` lines summarising an item, for display."""
    description = (info.get('description') or '').strip().replace('\n', ' ')
    if len(description) > 200:
        description = description[:200] + '...'

    width, height = info.get('width'), info.get('height')
    resolution = f'{width}x{height}' if width and height else 'unknown'
    views = info.get('view_count')

    rows = [
        ('title', info.get('title') or 'unknown'),
        ('source', info.get('extractor_key') or 'unknown'),
        ('channel', info.get('uploader') or info.get('channel') or 'unknown'),
        ('duration', format_duration(info.get('duration'))),
        ('views', f'{views:,}' if isinstance(views, int) else 'unknown'),
        ('resolution', resolution),
        ('uploaded', format_date(info.get('upload_date'))),
        ('summary', description or 'none'),
    ]
    return [(f'{key:>10} : {value}', 'info') for key, value in rows]


def available_heights(info, minimum=0):
    """Distinct video heights offered for this item, tallest first."""
    heights = set()
    for fmt in info.get('formats') or []:
        height = fmt.get('height')
        if height and fmt.get('vcodec', 'none') != 'none' and int(height) >= minimum:
            heights.add(int(height))
    if not heights and info.get('height'):
        heights.add(int(info['height']))
    return sorted(heights, reverse=True)


# --------------------------------------------------------------------------
# downloading
# --------------------------------------------------------------------------

def _video_format(quality):
    """Build a yt-dlp format selector, falling back to progressive streams."""
    if not quality or str(quality).lower() == 'best':
        return 'bestvideo*+bestaudio/best'
    height = int(quality)
    return f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best'


def _make_hooks(state, progress, is_cancelled):
    """Progress and postprocessor hooks that normalise yt-dlp's payloads."""

    def check_cancel():
        if is_cancelled and is_cancelled():
            raise Cancelled()

    def on_progress(payload):
        check_cancel()
        if payload.get('filename'):
            state['filename'] = payload['filename']
        if not progress:
            return
        total = payload.get('total_bytes') or payload.get('total_bytes_estimate')
        done = payload.get('downloaded_bytes') or 0
        progress({
            'status': payload.get('status'),
            'downloaded': done,
            'total': total,
            'fraction': (done / total) if total else None,
            'speed': payload.get('speed'),
            'eta': payload.get('eta'),
            'filename': os.path.basename(payload.get('filename') or ''),
        })

    def on_postprocess(payload):
        check_cancel()
        info = payload.get('info_dict') or {}
        if info.get('filepath'):
            state['filename'] = info['filepath']
        if progress and payload.get('status') == 'started':
            progress({
                'status': 'processing',
                'postprocessor': payload.get('postprocessor', 'ffmpeg'),
            })

    return on_progress, on_postprocess


def _run(url, opts, state, is_cancelled):
    _require_ytdlp()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Cancelled:
        raise
    except Exception as exc:
        # yt-dlp wraps hook exceptions, so re-check the flag before blaming it.
        if is_cancelled and is_cancelled():
            raise Cancelled() from exc
        raise
    return state.get('filename')


def _base_opts(outdir, log, progress, is_cancelled, state):
    on_progress, on_postprocess = _make_hooks(state, progress, is_cancelled)
    os.makedirs(outdir, exist_ok=True)
    return {
        'outtmpl': os.path.join(outdir, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': False,
        'noprogress': True,          # we render progress ourselves
        'logger': _Logger(log),
        'progress_hooks': [on_progress],
        'postprocessor_hooks': [on_postprocess],
        'concurrent_fragment_downloads': 4,
        'retries': 5,
        'ignoreerrors': False,
    }


def download_video(url, quality='best', outdir=None, log=None,
                   progress=None, is_cancelled=None):
    """Download the video stream at (at most) ``quality`` and merge to MKV."""
    log = log or _noop_log
    outdir = outdir or default_download_dir()
    state = {}
    opts = _base_opts(outdir, log, progress, is_cancelled, state)
    opts.update({
        'format': _video_format(quality),
        'merge_output_format': 'mkv',
    })
    log(f'format selector: {opts["format"]}', 'dim')
    return _run(url, opts, state, is_cancelled)


def download_audio(url, outdir=None, log=None, progress=None,
                   is_cancelled=None, bitrate='320'):
    """Download the best audio stream and transcode it to MP3."""
    log = log or _noop_log
    outdir = outdir or default_download_dir()
    state = {}
    opts = _base_opts(outdir, log, progress, is_cancelled, state)
    opts.update({
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': bitrate,
        }],
    })
    log(f'format selector: bestaudio/best -> mp3 @ {bitrate}kbps', 'dim')
    return _run(url, opts, state, is_cancelled)


def open_folder(path):
    """Reveal ``path`` in the platform file manager."""
    if not os.path.isdir(path):
        return False
    if sys.platform == 'win32':
        os.startfile(path)
    elif sys.platform == 'darwin':
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')
    return True
