# 🎵 TuneTube Downloader

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![yt-dlp](https://img.shields.io/badge/Engine-yt--dlp-red?style=for-the-badge)](https://github.com/yt-dlp/yt-dlp)
[![GUI](https://img.shields.io/badge/GUI-Tkinter-2ea44f?style=for-the-badge)](https://docs.python.org/3/library/tkinter.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**TuneTube** downloads video in maximum quality (up to 4K/8K) and audio as 320 kbps MP3, from YouTube, Instagram and the many other sites `yt-dlp` supports. It ships with **two front ends that share one engine**:

| | |
|---|---|
| 🖥️ **`gui.py`** | A desktop window styled like a command line — banner, live log, ASCII progress bar. |
| ⌨️ **`youtube.py`** | The original prompt-driven console flow. |

---

## 🖥️ The GUI

```bash
python gui.py
```

A dark, phosphor-green console theme — it looks like a terminal, but every control is clickable:

```
 ████████╗██╗   ██╗███╗   ██╗███████╗████████╗██╗   ██╗██████╗ ███████╗
 ╚══██╔══╝██║   ██║████╗  ██║██╔════╝╚══██╔══╝██║   ██║██╔══██╗██╔════╝
    ██║   ██║   ██║██╔██╗ ██║█████╗     ██║   ██║   ██║██████╔╝█████╗
    ██║   ██║   ██║██║╚██╗██║██╔══╝     ██║   ██║   ██║██╔══██╗██╔══╝
    ██║   ╚██████╔╝██║ ╚████║███████╗   ██║   ╚██████╔╝██████╔╝███████╗
    ╚═╝    ╚═════╝ ╚═╝  ╚═══╝╚══════╝   ╚═╝    ╚═════╝ ╚═════╝ ╚══════╝
 >> HIGH QUALITY MEDIA EXTRACTION ENGINE <<
 ────────────────────────────────────────────────────────────────────────
  url  $  https://www.youtube.com/watch?v=...
  mode $  [ ] audio  (mp3)      [x] video  (mkv)
  qual $  [ 1080p ▾ ]   [ fetch info ]   lists every resolution on offer
  out  $  ~/Downloads/TuneTube          [ browse ]  [ open ]
          [ ▸ download ]   [ ■ abort ]   [ clear ]
 ┌──────────────────────────────────────────────────────────────────────┐
 │ [12:04:31] $ tunetube get --video --quality 1080 https://...         │
 │ [12:04:32]      title : Example clip                                 │
 │ [12:04:32]     source : Youtube                                      │
 │ [12:04:32]   duration : 4:12                                         │
 │ [12:04:33] [download] Destination: Example clip.f313.webm            │
 └──────────────────────────────────────────────────────────────────────┘
 [████████████░░░░░░░░░░░░░░░░░░]   42.1%   3.2 MiB/s   eta 00:42
```

### What it does

* **Live log pane** — everything the engine reports is echoed with timestamps and colour-coded by severity (info, warning, error).
* **`fetch info`** — resolves the URL first, prints title / channel / duration / views / upload date, and fills the quality dropdown with **every resolution that URL actually offers**.
* **ASCII progress bar** — percentage, transfer speed, ETA and bytes done. Sources that do not report a total size get a sweeping bar instead of a fake percentage.
* **`abort`** — cancels a running download cleanly; the window never freezes, because downloads run on a worker thread.
* **Startup self-check** — reports whether `yt-dlp` and `ffmpeg` were found before you hit a failure.

### Keyboard

| Key | Action |
|---|---|
| `Enter` | Start the download |
| `Esc` | Abort the running job |
| `Ctrl` + `L` | Clear the log pane |

---

## ⌨️ The command line

```bash
python youtube.py
```

The original flow, unchanged: paste a URL, choose audio (`1`) or video (`2`), and for video pick a resolution from the list it prints. Resolution accepts `1080`, `1080p` or `best`.

---

## 🚀 Features

* **Auto-best quality** — `best` picks the highest available video and audio streams and merges them.
* **4K/8K support** — full Ultra HD via DASH merging (needs FFmpeg).
* **Smart codec selection** — prefers efficient codecs like VP9 and AV1 for a better quality-to-size ratio.
* **320 kbps MP3** — audio mode extracts the best audio stream and converts it with FFmpeg.
* **Many sources** — YouTube, Instagram and everything else `yt-dlp` supports.
* **Faster fragments** — downloads 4 fragments concurrently and retries transient failures.
* **Cross-platform** — Windows, Linux and macOS.

---

## 📁 Project structure

```
TuneTube-Downloader/
├── gui.py              # terminal-themed desktop front end (Tkinter)
├── youtube.py          # prompt-driven command line front end
├── tunetube_core.py    # shared download engine wrapping yt-dlp
├── requirements.txt
└── README.md
```

`tunetube_core.py` holds all of the extraction logic and never prints or touches
a widget — each front end passes in its own `log` and `progress` callbacks. That
is why the GUI and the CLI cannot drift apart.

---

## 📦 Installation & Setup

### 1. Prerequisites

**FFmpeg** is required to merge high-resolution streams (>1080p) and to produce MP3s.

| Platform | Command |
|---|---|
| Windows | `winget install Gyan.FFmpeg` (or `choco install ffmpeg`) |
| Fedora | `sudo dnf install ffmpeg` |
| Arch Linux | `sudo pacman -S ffmpeg` |
| Debian/Ubuntu | `sudo apt install ffmpeg` |
| macOS | `brew install ffmpeg` |

**Tkinter** powers the GUI. It ships with Python on Windows and macOS; on Debian/Ubuntu install it with `sudo apt install python3-tk`.

### 2. Clone the repository

```bash
git clone https://github.com/Nirushanth-07/TuneTube-Downloader.git
cd TuneTube-Downloader
```

### 3. Create a virtual environment

```bash
python -m venv .venv

# Activate it - Linux/macOS
source .venv/bin/activate

# Activate it - Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Verify

```bash
python -c "import yt_dlp, tkinter; print('yt-dlp', yt_dlp.version.__version__, '| tkinter', tkinter.TkVersion)"
ffmpeg -version
```

---

## 📤 Output

Downloads land in **`~/Downloads/TuneTube`** by default (change it in the GUI's `out` field). Files are named after the title of the media.

| Mode | Container | Notes |
|---|---|---|
| Video | `.mkv` | Best video + best audio, merged by FFmpeg |
| Audio | `.mp3` | 320 kbps, converted by FFmpeg |

---

## 🩺 Troubleshooting

| Symptom | Fix |
|---|---|
| `yt-dlp ... MISSING` on startup | `pip install -r requirements.txt` — and check your virtual environment is active. |
| `ffmpeg ... not found on PATH` | Install FFmpeg (table above). Without it, >1080p merging and MP3 conversion fail. |
| `ModuleNotFoundError: No module named 'tkinter'` | Debian/Ubuntu: `sudo apt install python3-tk`. |
| A download fails on a site that used to work | Sites change constantly: `pip install --upgrade yt-dlp`. |
| Private or login-walled Instagram post | TuneTube only downloads publicly accessible media. |

---

### Contributions, issues, and feature requests are welcome! Feel free to check the issues page.
