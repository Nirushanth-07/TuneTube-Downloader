"""TuneTube Downloader - terminal themed desktop front end.

A Tk window dressed as a phosphor-green console: ASCII banner, a scrolling log
pane that echoes everything yt-dlp says, and an ASCII progress bar. All of the
actual work happens in :mod:`tunetube_core`, on a worker thread; the worker only
ever pushes messages onto a queue, and the Tk main loop drains it, so no widget
is ever touched from a background thread.

Run it with:  python gui.py
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, font as tkfont

import tunetube_core as core

APP_VERSION = '1.0'

# --------------------------------------------------------------------------
# theme
# --------------------------------------------------------------------------

BG = '#070b08'          # window / console background
PANEL = '#0c130e'       # inputs and buttons
FG = '#3bf07a'          # primary phosphor green
DIM = '#1f7a44'         # labels, borders, chrome
BRIGHT = '#c7ffd9'      # entry text
CYAN = '#3fd7e8'
YELLOW = '#f2c14e'
RED = '#ff5f56'
SELECT = '#154d2c'      # selection / pressed state

BAR_WIDTH = 30
BAR_FULL = '█'     # full block
BAR_EMPTY = '░'    # light shade

BANNER = r"""
 ████████╗██╗   ██╗███╗   ██╗███████╗████████╗██╗   ██╗██████╗ ███████╗
 ╚══██╔══╝██║   ██║████╗  ██║██╔════╝╚══██╔══╝██║   ██║██╔══██╗██╔════╝
    ██║   ██║   ██║██╔██╗ ██║█████╗     ██║   ██║   ██║██████╔╝█████╗
    ██║   ██║   ██║██║╚██╗██║██╔══╝     ██║   ██║   ██║██╔══██╗██╔══╝
    ██║   ╚██████╔╝██║ ╚████║███████╗   ██║   ╚██████╔╝██████╔╝███████╗
    ╚═╝    ╚═════╝ ╚═╝  ╚═══╝╚══════╝   ╚═╝    ╚═════╝ ╚═════╝ ╚══════╝
"""

TAGLINE = '>> HIGH QUALITY MEDIA EXTRACTION ENGINE <<'


def pick_font():
    """First monospace family actually installed, so the art stays aligned."""
    families = set(tkfont.families())
    for name in ('Cascadia Mono', 'Consolas', 'DejaVu Sans Mono',
                 'Liberation Mono', 'Menlo', 'Courier New'):
        if name in families:
            return name
    return 'TkFixedFont'


class TuneTubeGUI:
    def __init__(self, root):
        self.root = root
        self.mono = pick_font()
        # Point sizes, so text tracks the user's display scaling; the window
        # is then sized from the finished layout in _fit_window(), which is
        # what keeps a scaled UI from outgrowing its geometry.
        self.font = (self.mono, 10)
        self.font_small = (self.mono, 9)
        self.font_banner = (self.mono, 9)

        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.busy = False
        self.last_file = None
        self.spin = 0

        self._build_window()
        self._build_banner()
        self._build_form()
        self._build_console()
        self._build_status()
        self._bind_keys()

        self._fit_window()
        self.root.after(60, self._pump)
        self._blink()
        self._greet()

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------

    def _build_window(self):
        self.root.title('TuneTube Downloader')
        self.root.configure(bg=BG)
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)   # console expands

    def _fit_window(self):
        '''Size to what the widgets actually asked for, then centre.

        A hardcoded geometry clipped the buttons on scaled displays, so let
        the built layout state its own width and honour it.
        '''
        self.root.update_idletasks()
        need_w = self.root.winfo_reqwidth()
        need_h = self.root.winfo_reqheight()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(max(need_w, 900), screen_w - 60)
        height = min(max(need_h, 660), screen_h - 120)
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 3)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        self.root.minsize(min(need_w, width), 520)

    def _rule(self, parent, row, pady=(0, 0)):
        line = tk.Frame(parent, bg=DIM, height=1)
        line.grid(row=row, column=0, sticky='ew', padx=14, pady=pady)
        return line

    def _build_banner(self):
        head = tk.Frame(self.root, bg=BG)
        head.grid(row=0, column=0, sticky='ew', padx=14, pady=(10, 4))
        head.columnconfigure(0, weight=1)

        tk.Label(head, text=BANNER.strip('\n'), font=self.font_banner, bg=BG,
                 fg=FG, justify='left', anchor='w').grid(row=0, column=0,
                                                        sticky='w')
        tk.Label(head, text=TAGLINE, font=self.font_small, bg=BG, fg=DIM,
                 anchor='w').grid(row=1, column=0, sticky='w', pady=(4, 0))
        self._rule(self.root, 1, pady=(6, 0))

    def _label(self, parent, text, fg=DIM):
        return tk.Label(parent, text=text, font=self.font, bg=BG, fg=fg,
                        anchor='e')

    def _entry(self, parent, textvariable):
        entry = tk.Entry(parent, textvariable=textvariable, font=self.font,
                         bg=PANEL, fg=BRIGHT, insertbackground=FG,
                         relief='flat', bd=0, highlightthickness=1,
                         highlightbackground=DIM, highlightcolor=FG,
                         selectbackground=SELECT, selectforeground=BRIGHT)
        return entry

    def _button(self, parent, text, command, fg=FG):
        return tk.Button(parent, text=text, command=command, font=self.font,
                         bg=PANEL, fg=fg, activebackground=fg,
                         activeforeground=BG, disabledforeground='#1a4a2c',
                         relief='flat', bd=0, highlightthickness=1,
                         highlightbackground=DIM, highlightcolor=fg,
                         padx=12, pady=3, cursor='hand2')

    def _build_form(self):
        form = tk.Frame(self.root, bg=BG)
        form.grid(row=2, column=0, sticky='ew', padx=14, pady=(10, 8))
        form.columnconfigure(1, weight=1)

        # --- url -------------------------------------------------------
        self.url_var = tk.StringVar()
        self._label(form, 'url  $').grid(row=0, column=0, sticky='e',
                                         padx=(0, 8), pady=3)
        self.url_entry = self._entry(form, self.url_var)
        self.url_entry.grid(row=0, column=1, sticky='ew', ipady=4, pady=3)

        # --- mode + quality --------------------------------------------
        self._label(form, 'mode $').grid(row=1, column=0, sticky='e',
                                         padx=(0, 8), pady=3)
        row = tk.Frame(form, bg=BG)
        row.grid(row=1, column=1, sticky='ew', pady=3)

        self.mode_var = tk.StringVar(value='video')
        self.mode_buttons = {}
        for index, (value, caption) in enumerate((('audio', 'audio  (mp3)'),
                                                  ('video', 'video  (mkv)'))):
            button = tk.Radiobutton(
                row, text=f'[ ] {caption}', variable=self.mode_var,
                value=value, indicatoron=False, font=self.font, bg=PANEL,
                fg=FG, selectcolor=SELECT, activebackground=SELECT,
                activeforeground=BRIGHT, relief='flat', bd=0,
                highlightthickness=1, highlightbackground=DIM,
                padx=10, pady=3, anchor='w', cursor='hand2',
                command=self._sync_mode)
            button.grid(row=0, column=index, padx=(0, 8))
            self.mode_buttons[value] = (button, caption)

        # --- quality ----------------------------------------------------
        self._label(form, 'qual $').grid(row=2, column=0, sticky='e',
                                         padx=(0, 8), pady=3)
        qrow = tk.Frame(form, bg=BG)
        qrow.grid(row=2, column=1, sticky='ew', pady=3)

        self.quality_var = tk.StringVar(value='best')
        self.quality_menu = tk.OptionMenu(qrow, self.quality_var, 'best')
        self.quality_menu.config(font=self.font, bg=PANEL, fg=FG,
                                 activebackground=FG, activeforeground=BG,
                                 relief='flat', bd=0, highlightthickness=1,
                                 highlightbackground=DIM, width=8,
                                 anchor='w', direction='below', cursor='hand2')
        self.quality_menu['menu'].config(font=self.font, bg=PANEL, fg=FG,
                                         activebackground=FG,
                                         activeforeground=BG, bd=0,
                                         relief='flat')
        self.quality_menu.grid(row=0, column=0)

        self.fetch_button = self._button(qrow, '[ fetch info ]',
                                         self.on_fetch, fg=CYAN)
        self.fetch_button.grid(row=0, column=1, padx=(8, 0))
        tk.Label(qrow, text='lists every resolution this url offers',
                 font=self.font_small, bg=BG,
                 fg=DIM).grid(row=0, column=2, padx=(12, 0))

        # --- output directory ------------------------------------------
        self._label(form, 'out  $').grid(row=3, column=0, sticky='e',
                                         padx=(0, 8), pady=3)
        out = tk.Frame(form, bg=BG)
        out.grid(row=3, column=1, sticky='ew', pady=3)
        out.columnconfigure(0, weight=1)

        self.outdir_var = tk.StringVar(value=core.default_download_dir())
        self._entry(out, self.outdir_var).grid(row=0, column=0, sticky='ew',
                                               ipady=4)
        self._button(out, '[ browse ]', self.on_browse).grid(row=0, column=1,
                                                             padx=(8, 0))
        self._button(out, '[ open ]', self.on_open_folder).grid(row=0,
                                                                column=2,
                                                                padx=(8, 0))

        # --- actions ----------------------------------------------------
        actions = tk.Frame(form, bg=BG)
        actions.grid(row=4, column=1, sticky='ew', pady=(12, 0))

        self.download_button = self._button(actions, '[ ▸ download ]',
                                            self.on_download)
        self.download_button.grid(row=0, column=0)
        self.abort_button = self._button(actions, '[ ■ abort ]',
                                         self.on_abort, fg=RED)
        self.abort_button.grid(row=0, column=1, padx=(8, 0))
        self.abort_button.config(state='disabled')
        self._button(actions, '[ clear ]', self.on_clear,
                     fg=DIM).grid(row=0, column=2, padx=(8, 0))
        tk.Label(actions,
                 text='enter = download   esc = abort   ctrl+l = clear',
                 font=self.font_small, bg=BG,
                 fg=DIM).grid(row=0, column=3, padx=(16, 0))

        self._sync_mode()

    def _build_console(self):
        wrap = tk.Frame(self.root, bg=DIM, padx=1, pady=1)
        wrap.grid(row=3, column=0, sticky='nsew', padx=14, pady=(4, 8))
        wrap.columnconfigure(0, weight=1)
        wrap.rowconfigure(0, weight=1)

        self.console = tk.Text(
            wrap, bg=BG, fg=FG, insertbackground=FG, relief='flat', bd=0,
            highlightthickness=0, wrap='word', font=self.font, padx=10,
            pady=8, spacing1=1, state='disabled', selectbackground=SELECT,
            selectforeground=BRIGHT, height=14, width=1)
        self.console.grid(row=0, column=0, sticky='nsew')

        bar = tk.Scrollbar(wrap, command=self.console.yview, width=11,
                           troughcolor=BG, bg=DIM, activebackground=FG,
                           relief='flat', bd=0, highlightthickness=0,
                           elementborderwidth=0)
        bar.grid(row=0, column=1, sticky='ns')
        self.console.config(yscrollcommand=bar.set)

        for tag, colour in (('info', FG), ('dim', DIM), ('ok', '#8effb0'),
                            ('warn', YELLOW), ('error', RED), ('cmd', CYAN),
                            ('time', '#15633a')):
            self.console.tag_config(tag, foreground=colour)

    def _build_status(self):
        status = tk.Frame(self.root, bg=BG)
        status.grid(row=4, column=0, sticky='ew', padx=14, pady=(0, 12))
        status.columnconfigure(1, weight=1)

        self.progress_var = tk.StringVar(value=self._empty_bar())
        tk.Label(status, textvariable=self.progress_var, font=self.font,
                 bg=BG, fg=FG, anchor='w').grid(row=0, column=0,
                                                columnspan=2, sticky='w')

        self.state_var = tk.StringVar(value='idle')
        self.state_label = tk.Label(status, textvariable=self.state_var,
                                    font=self.font, bg=BG, fg=DIM, anchor='w')
        self.state_label.grid(row=1, column=0, sticky='w', pady=(6, 0))

        self.cursor_label = tk.Label(status, text='█', font=self.font,
                                     bg=BG, fg=FG)
        self.cursor_label.grid(row=1, column=1, sticky='w', pady=(6, 0))

    def _bind_keys(self):
        self.root.bind('<Return>', lambda _e: self.on_download())
        self.root.bind('<Escape>', lambda _e: self.on_abort())
        self.root.bind('<Control-l>', lambda _e: self.on_clear())
        self.url_entry.focus_set()

    # ------------------------------------------------------------------
    # console
    # ------------------------------------------------------------------

    def log(self, text, level='info'):
        """Append a line to the console. Main thread only."""
        for line in str(text).rstrip().split('\n'):
            at_bottom = self.console.yview()[1] > 0.999
            self.console.config(state='normal')
            self.console.insert('end', time.strftime('[%H:%M:%S] '), 'time')
            self.console.insert('end', line + '\n', level)
            self.console.config(state='disabled')
            if at_bottom:
                self.console.see('end')

    def log_from_worker(self, text, level='info'):
        """yt-dlp callbacks land here, off the main thread."""
        self.events.put(('log', (text, level)))

    def _greet(self):
        self.log('TuneTube ' + APP_VERSION + ' - media extraction engine', 'cmd')
        version = sys.version.split()[0]
        self.log(f'python {version} on {sys.platform}', 'dim')

        ytdlp = core.ytdlp_version()
        if ytdlp:
            self.log(f'yt-dlp {ytdlp} ... ok', 'dim')
        else:
            self.log('yt-dlp ... MISSING - run:  pip install yt-dlp', 'error')

        if core.ffmpeg_available():
            self.log('ffmpeg ... ok', 'dim')
        else:
            self.log('ffmpeg ... not found on PATH', 'warn')
            self.log('  4K/8K merging and mp3 conversion need ffmpeg', 'warn')

        self.log(f'output -> {self.outdir_var.get()}', 'dim')
        self.log('ready. paste a url, pick a mode, hit download.', 'ok')

    # ------------------------------------------------------------------
    # small ui helpers
    # ------------------------------------------------------------------

    def _sync_mode(self):
        """Redraw the radio captions as [x] / [ ] checkboxes."""
        current = self.mode_var.get()
        for value, (button, caption) in self.mode_buttons.items():
            mark = 'x' if value == current else ' '
            button.config(text=f'[{mark}] {caption}')
        video = current == 'video'
        self.quality_menu.config(state='normal' if video else 'disabled')

    def _empty_bar(self):
        return f'[{BAR_EMPTY * BAR_WIDTH}]'

    def _blink(self):
        colour = self.cursor_label.cget('fg')
        self.cursor_label.config(fg=BG if colour == FG else FG)
        self.root.after(550, self._blink)

    def _set_state(self, text, colour=DIM):
        self.state_var.set(text)
        self.state_label.config(fg=colour)

    def _set_busy(self, busy):
        self.busy = busy
        for widget in (self.download_button, self.fetch_button):
            widget.config(state='disabled' if busy else 'normal')
        self.abort_button.config(state='normal' if busy else 'disabled')

    def _set_quality_options(self, heights):
        values = ['best'] + [f'{height}p' for height in heights]
        menu = self.quality_menu['menu']
        menu.delete(0, 'end')
        for value in values:
            menu.add_command(label=value, foreground=FG, background=PANEL,
                             activeforeground=BG, activebackground=FG,
                             command=tk._setit(self.quality_var, value))
        if self.quality_var.get() not in values:
            self.quality_var.set('best')

    def _quality_argument(self):
        value = self.quality_var.get()
        return 'best' if value == 'best' else value.rstrip('p')

    def _render_progress(self, payload):
        status = payload.get('status')

        if status == 'processing':
            step = payload.get('postprocessor', 'ffmpeg')
            self.progress_var.set(
                f'[{BAR_FULL * BAR_WIDTH}]  post-processing ({step})')
            self._set_state(f'running {step} ...', CYAN)
            return

        if status == 'finished':
            self.progress_var.set(f'[{BAR_FULL * BAR_WIDTH}]  100.0%  stream done')
            return

        fraction = payload.get('fraction')
        speed = payload.get('speed')
        speed_text = f'{core.format_bytes(speed)}/s' if speed else '-- B/s'
        eta = payload.get('eta')
        eta_text = f'{int(eta) // 60:02d}:{int(eta) % 60:02d}' if eta else '--:--'
        done = core.format_bytes(payload.get('downloaded'))

        if fraction is None:
            # Unknown size: sweep a block back and forth instead of lying.
            self.spin = (self.spin + 1) % (BAR_WIDTH - 3)
            cells = list(BAR_EMPTY * BAR_WIDTH)
            cells[self.spin:self.spin + 4] = BAR_FULL * 4
            bar = ''.join(cells[:BAR_WIDTH])
            self.progress_var.set(f'[{bar}]   ----   {speed_text}   {done}')
        else:
            filled = int(fraction * BAR_WIDTH)
            bar = BAR_FULL * filled + BAR_EMPTY * (BAR_WIDTH - filled)
            total = core.format_bytes(payload.get('total'))
            self.progress_var.set(
                f'[{bar}]  {fraction * 100:5.1f}%   {speed_text}   '
                f'eta {eta_text}   {done} / {total}')

        name = payload.get('filename')
        self._set_state(f'downloading {name}' if name else 'downloading ...', FG)

    # ------------------------------------------------------------------
    # queue pump - the only place worker messages reach the widgets
    # ------------------------------------------------------------------

    def _pump(self):
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if kind == 'log':
                self.log(*payload)
            elif kind == 'progress':
                self._render_progress(payload)
            elif kind == 'qualities':
                self._set_quality_options(payload)
            elif kind == 'done':
                self._on_worker_done(payload)

        self.root.after(60, self._pump)

    def _on_worker_done(self, payload):
        outcome, detail = payload
        self._set_busy(False)
        self.worker = None

        if outcome == 'ok':
            self.progress_var.set(f'[{BAR_FULL * BAR_WIDTH}]  100.0%  complete')
            self._set_state('done', FG)
        elif outcome == 'cancelled':
            self.progress_var.set(self._empty_bar())
            self._set_state('aborted', YELLOW)
        elif outcome == 'info':
            self.progress_var.set(self._empty_bar())
            self._set_state('idle', DIM)
        else:
            self.progress_var.set(self._empty_bar())
            self._set_state('failed', RED)
        if detail:
            self.last_file = detail

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------

    def _start(self, target, *args):
        if self.busy:
            self.log('a job is already running - abort it first', 'warn')
            return False
        self.cancel.clear()
        self._set_busy(True)
        self.worker = threading.Thread(target=target, args=args, daemon=True)
        self.worker.start()
        return True

    def _url(self):
        url = self.url_var.get().strip()
        if not url:
            self.log('no url given', 'error')
            self.url_entry.focus_set()
            return None
        return url

    def on_fetch(self):
        url = self._url()
        if url:
            self.log(f'$ tunetube info {url}', 'cmd')
            self._set_state('resolving ...', CYAN)
            self._start(self._work_fetch, url)

    def on_download(self):
        if self.busy:
            self.log('a job is already running - abort it first', 'warn')
            return
        url = self._url()
        if not url:
            return
        mode = self.mode_var.get()
        outdir = self.outdir_var.get().strip() or core.default_download_dir()

        if mode == 'audio':
            self.log(f'$ tunetube get --audio {url}', 'cmd')
            self._start(self._work_audio, url, outdir)
        else:
            quality = self._quality_argument()
            self.log(f'$ tunetube get --video --quality {quality} {url}', 'cmd')
            self._start(self._work_video, url, quality, outdir)

    def on_abort(self):
        if not self.busy:
            return
        self.cancel.set()
        self.log('^C  abort requested - stopping after the current chunk',
                 'warn')
        self._set_state('aborting ...', YELLOW)

    def on_clear(self):
        self.console.config(state='normal')
        self.console.delete('1.0', 'end')
        self.console.config(state='disabled')
        self.log('console cleared', 'dim')

    def on_browse(self):
        chosen = filedialog.askdirectory(
            title='Choose download folder',
            initialdir=self.outdir_var.get() or os.path.expanduser('~'))
        if chosen:
            self.outdir_var.set(os.path.normpath(chosen))
            self.log(f'output -> {self.outdir_var.get()}', 'dim')

    def on_open_folder(self):
        path = self.outdir_var.get().strip()
        try:
            os.makedirs(path, exist_ok=True)
            core.open_folder(path)
        except OSError as exc:
            self.log(f'cannot open {path}: {exc}', 'error')

    def _on_close(self):
        self.cancel.set()
        self.root.destroy()

    # ------------------------------------------------------------------
    # worker bodies - background thread, queue only
    # ------------------------------------------------------------------

    def _progress_from_worker(self, payload):
        self.events.put(('progress', payload))

    def _finish(self, outcome, detail=None):
        self.events.put(('done', (outcome, detail)))

    def _handle_failure(self, exc):
        if isinstance(exc, core.MissingDependency):
            self.log_from_worker(str(exc), 'error')
        elif isinstance(exc, core.Cancelled):
            self.log_from_worker('aborted by user', 'warn')
            self._finish('cancelled')
            return
        else:
            self.log_from_worker(f'error: {exc}', 'error')
        self._finish('error')

    def _work_fetch(self, url):
        try:
            info = core.fetch_info(url, self.log_from_worker)
            for line, level in core.describe(info):
                self.log_from_worker(line, level)

            heights = core.available_heights(info)
            self.events.put(('qualities', heights))
            if heights:
                listed = '  '.join(f'{height}p' for height in heights)
                self.log_from_worker(f'available: {listed}', 'ok')
            else:
                self.log_from_worker(
                    'no per-height formats listed - use quality "best"', 'warn')
            self._finish('info')
        except Exception as exc:
            self._handle_failure(exc)

    def _work_video(self, url, quality, outdir):
        try:
            path = core.download_video(
                url, quality=quality, outdir=outdir,
                log=self.log_from_worker, progress=self._progress_from_worker,
                is_cancelled=self.cancel.is_set)
            self._report_saved(path, outdir)
            self._finish('ok', path)
        except Exception as exc:
            self._handle_failure(exc)

    def _work_audio(self, url, outdir):
        try:
            path = core.download_audio(
                url, outdir=outdir, log=self.log_from_worker,
                progress=self._progress_from_worker,
                is_cancelled=self.cancel.is_set)
            self._report_saved(path, outdir)
            self._finish('ok', path)
        except Exception as exc:
            self._handle_failure(exc)

    def _report_saved(self, path, outdir):
        where = path or outdir
        self.log_from_worker('download complete', 'ok')
        self.log_from_worker(f'saved -> {where}', 'ok')


def main():
    root = tk.Tk()
    TuneTubeGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
