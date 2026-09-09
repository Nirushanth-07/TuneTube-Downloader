"""TuneTube Downloader - command line entry point.

The extraction logic lives in :mod:`tunetube_core`, shared with the desktop
front end in ``gui.py``, so both interfaces behave identically.

    python youtube.py      # this prompt-driven console flow
    python gui.py          # the terminal themed window
"""

import sys

import tunetube_core as core

BANNER = r"""
_________  ___  ___  ________   _______           _________  ___  ___  ________  _______      
|\___   ___\\  \|\  \|\   ___  \|\  ___ \         |\___   ___\\  \|\  \|\   __  \|\  ___ \     
\|___ \  \_\ \  \\\  \ \  \\ \  \ \   __/|        \|___ \  \_\ \  \\\  \ \  \|\  \ \   __/|    
     \ \  \ \ \  \\\  \ \  \\ \  \ \  \_|/__           \ \  \ \ \  \\\  \ \   __  \ \  \_|/__  
      \ \  \ \ \  \\\  \ \  \\ \  \ \  \_|\ \           \ \  \ \ \  \\\  \ \  \|\  \ \  \_|\ \ 
       \ \__\ \ \_______\ \__\\ \__\ \_______\           \ \__\ \ \_______\ \_______\ \_______\
        \|__|  \|_______|\|__| \|__|\|_______|            \|__|  \|_______|\|_______|\|_______|
                                                                                               
                            >> HIGH QUALITY MEDIA EXTRACTION ENGINE <<
"""

BAR_WIDTH = 28


def log(text, level='info'):
    """Print engine output. Errors go to stderr so redirects stay useful."""
    print(text, file=sys.stderr if level == 'error' else sys.stdout)


def make_progress():
    """A single redrawing status line, so the log does not scroll away.

    Plain ASCII on purpose: a Windows console using a legacy code page raises
    UnicodeEncodeError on block-drawing characters.
    """
    def progress(payload):
        status = payload.get('status')

        if status == 'processing':
            step = payload.get('postprocessor', 'ffmpeg')
            sys.stdout.write('\r' + ' ' * 78 + '\r')
            print(f'Post-processing ({step}) ...')
            return

        if status == 'finished':
            sys.stdout.write('\r' + ' ' * 78 + '\r')
            print('Stream complete, finalising ...')
            return

        fraction = payload.get('fraction')
        speed = payload.get('speed')
        speed_text = f'{core.format_bytes(speed)}/s' if speed else '-- B/s'
        done = core.format_bytes(payload.get('downloaded'))

        if fraction is None:
            line = f'  downloading ... {done} at {speed_text}'
        else:
            filled = int(fraction * BAR_WIDTH)
            bar = '#' * filled + '-' * (BAR_WIDTH - filled)
            eta = payload.get('eta')
            eta_text = (f'{int(eta) // 60:02d}:{int(eta) % 60:02d}'
                        if eta else '--:--')
            total = core.format_bytes(payload.get('total'))
            line = (f'  [{bar}] {fraction * 100:5.1f}%  {speed_text}  '
                    f'eta {eta_text}  {done}/{total}')

        sys.stdout.write('\r' + line.ljust(78))
        sys.stdout.flush()

    return progress


def get_video_information(url):
    """Print a summary of ``url`` and return the resolutions on offer."""
    info = core.fetch_info(url, log)

    print()
    for line, _level in core.describe(info):
        print(line)

    heights = core.available_heights(info, minimum=360)
    if heights:
        print(f"\nSupported resolutions for: {info.get('title')}")
        for height in heights:
            print(f'- {height}p')
    else:
        print("\nNo per-height formats listed - use 'best' for this one.")
    return heights


def download_video(url, quality):
    """Download ``url`` at (at most) ``quality`` and merge to MKV."""
    print(f'\nStarting download: {url}')
    path = core.download_video(url, quality=quality, log=log,
                               progress=make_progress())
    print(f'\nDownload and merge complete!\nSaved -> {path}\n')


def download_audio(url):
    """Download the best audio for ``url`` and convert it to MP3."""
    print(f'\nStarting download: {url}')
    path = core.download_audio(url, log=log, progress=make_progress())
    print(f'\nSuccessfully downloaded and converted to MP3!\nSaved -> {path}\n')


def main():
    print(BANNER)
    print('\n')

    if not core.ffmpeg_available():
        print('Warning: ffmpeg was not found on PATH.')
        print('         4K/8K merging and MP3 conversion both need it.\n')

    url = input('Enter the video URL: ').strip()
    if not url:
        print('\nNo URL given.\n')
        return 1

    option = input(
        "Do you want do download Video/Audio ('1' : Audio, '2': Video): "
    ).strip()

    if option == '2':
        get_video_information(url)
        quality = input(
            "Enter the resolution of the video (digits only, eg: 1080, 1440,.. "
            "or 'best'): "
        ).strip().lower().rstrip('p')

        if quality == 'best':
            download_video(url, 'best')
        elif quality.isdigit() and int(quality) >= 360:
            download_video(url, quality)
        else:
            print('Invalid resolution.')
            return 1
    elif option == '1':
        download_audio(url)
    else:
        print('\nInvalid Option\n')
        return 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except core.MissingDependency as exc:
        print(f'\n{exc}\n', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\n\nAborted.\n')
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001 - the CLI reports, never traces
        print(f'\nAn error occurred: {exc}\n', file=sys.stderr)
        sys.exit(1)
