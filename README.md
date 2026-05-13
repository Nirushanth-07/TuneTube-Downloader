# 🎵 TuneTube Downloader

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![yt-dlp](https://img.shields.io/badge/Engine-yt--dlp-red?style=for-the-badge)](https://github.com/yt-dlp/yt-dlp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**TuneTube** is a high-performance command-line utility for downloading YouTube videos in maximum quality (up to 4K/8K). Built with Python, it leverages the power of `yt-dlp` to provide a seamless, "auto-quality" experience.

---

## 🚀 Features

*   **Auto-Best Quality:** Automatically detects and downloads the highest available resolution.
*   **4K/8K Support:** Full support for Ultra HD streams via DASH merging.
*   **Smart Codec Selection:** Prioritizes efficient codecs like VP9 and AV1 for superior quality-to-size ratios.
*   **Metadata Extraction:** Optionally fetches video info, thumbnails, and descriptions.
*   **Linux Optimized:** Designed to run smoothly on Linux and other high-performance environments.

## 📦 Installation & Setup

Follow these steps to set up the environment and get the downloader running on your machine.

### 1. Prerequisites
High-resolution downloads (4K/8K) require **FFmpeg** to merge video and audio streams.

*   **Fedora:** `sudo dnf install ffmpeg`
*   **Arch Linux:** `sudo pacman -S ffmpeg`
*   **Debian/Ubuntu:** `sudo apt install ffmpeg`

### 2. Clone the Repository
```bash
git clone [https://github.com/Nirushanth-07/TuneTube-Downloader.git](https://github.com/Nirushanth-07/TuneTube-Downloader.git)
cd Tune-Tube-Downloader
```

### 3. Create a Virtual Environment
```bash
# Create the environment
python -m venv .venv
# Activate the environment (Linux/macOS)
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install --upgrade pip
pip install yt-dlp
```

### 5. Verify Installation
```bash
python -c "import yt_dlp; print('yt-dlp version:', yt_dlp.version.__version__)"
```


## 🚀 Running the Script
With the virtual environment active, run the main script:
```bash
python youtube.py
```


### Contributions, issues, and feature requests are welcome! Feel free to check the issues page.