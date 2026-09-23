"""Live HUD: microphone waveform, FFT with command bands, and bot status."""

import tkinter as tk

import numpy as np

from .commands import Bands, Command
from .pitch import MAX_HZ, MIN_RMS, SAMPLE_RATE

FULL_SCALE = 32768.0
DB_FLOOR = -100.0
BAND_STYLE = {
    Command.STOP: ("STOP", "#5a1f1f"),
    Command.LEFT: ("LEFT", "#1f3a5a"),
    Command.RIGHT: ("RIGHT", "#1f5a3a"),
    Command.SPEED_UP: ("FASTER", "#5a4a1f"),
    Command.GOAL: ("GOAL", "#4a1f5a"),
}


def waveform_points(samples, width, height):
    """Flat [x0, y0, x1, y1, ...] canvas coordinates for the waveform."""
    x = np.asarray(samples, dtype=np.float64)
    if x.size < 2:
        return [0, height / 2, width, height / 2]
    idx = np.linspace(0, x.size - 1, min(width, x.size)).astype(int)
    xs = np.linspace(0, width, idx.size)
    ys = height / 2 - (x[idx] / FULL_SCALE) * (height / 2)
    return np.column_stack([xs, ys]).ravel().tolist()


def spectrum_db(samples, sample_rate=SAMPLE_RATE):
    """(freqs, level in dB full-scale) of a windowed chunk."""
    x = np.asarray(samples, dtype=np.float64)
    mags = np.abs(np.fft.rfft(x * np.hanning(x.size))) / (x.size / 4 * FULL_SCALE)
    freqs = np.fft.rfftfreq(x.size, 1.0 / sample_rate)
    return freqs, 20 * np.log10(mags + 1e-12)


def freq_to_x(freq, width, max_hz=MAX_HZ):
    return freq / max_hz * width


def db_to_y(db, height, floor=DB_FLOOR):
    return float(np.clip(db / floor, 0.0, 1.0)) * height


def spectrum_points(samples, width, height, sample_rate=SAMPLE_RATE, max_hz=MAX_HZ):
    """Flat canvas coordinates for the FFT from 0 to ``max_hz``."""
    freqs, db = spectrum_db(samples, sample_rate)
    keep = freqs <= max_hz
    xs = freq_to_x(freqs[keep], width, max_hz)
    ys = np.clip(db[keep] / DB_FLOOR, 0.0, 1.0) * height
    return np.column_stack([xs, ys]).ravel().tolist()


def band_regions(bands=Bands()):
    """(label, lo_hz, hi_hz, colour) for shading the FFT plot, low to high."""
    return [(BAND_STYLE[cmd][0], lo, hi, BAND_STYLE[cmd][1])
            for cmd, (lo, hi) in bands.items()]


class Hud:
    """Tk window refreshed every ``interval_ms`` from the control loop's state."""

    W, H = 720, 200

    def __init__(self, root, app, loop, mic_name, sample_rate=SAMPLE_RATE,
                 interval_ms=50, on_close=None, bands=Bands(), min_rms=MIN_RMS):
        self.root, self.app, self.loop = root, app, loop
        self.sample_rate = sample_rate
        self.min_rms = min_rms
        self.interval_ms = interval_ms
        root.title(f"whistle_bot HUD: {app.game.role.value}")
        root.configure(bg="#111")
        root.protocol("WM_DELETE_WINDOW", on_close or root.destroy)

        font = ("Menlo", 12)
        self.status = tk.Label(root, font=font, fg="#eee", bg="#111", anchor="w", justify="left")
        self.status.pack(fill="x", padx=8, pady=(8, 4))
        info = tk.Frame(root, bg="#111")
        info.pack(fill="x", padx=8)
        tk.Label(info, text=f"Mic: {mic_name}   (press q to quit)", font=font, fg="#888",
                 bg="#111", anchor="w").pack(side="left")
        tk.Button(info, text="Quit (q)", command=on_close or root.destroy).pack(side="right")

        tk.Label(root, text="Waveform", fg="#aaa", bg="#111", anchor="w").pack(fill="x", padx=8)
        self.wave = tk.Canvas(root, width=self.W, height=self.H, bg="black", highlightthickness=0)
        self.wave.pack(padx=8)
        self.wave.create_line(0, self.H / 2, self.W, self.H / 2, fill="#333")
        self.wave_line = self.wave.create_line(0, 0, 0, 0, fill="#3cf", width=1)

        tk.Label(root, text=f"FFT (0–{MAX_HZ:.0f} Hz, dBFS)", fg="#aaa", bg="#111",
                 anchor="w").pack(fill="x", padx=8, pady=(6, 0))
        self.fft = tk.Canvas(root, width=self.W, height=self.H, bg="black", highlightthickness=0)
        self.fft.pack(padx=8, pady=(0, 8))
        for label, lo, hi, colour in band_regions(bands):
            x0, x1 = freq_to_x(lo, self.W), freq_to_x(hi, self.W)
            self.fft.create_rectangle(x0, 0, x1, self.H, fill=colour, outline="")
            self.fft.create_text((x0 + x1) / 2, 10, text=label, fill="#ccc", font=("Menlo", 10))
        self.fft_line = self.fft.create_line(0, 0, 0, 0, fill="#fc3", width=1)
        self.peak_marker = self.fft.create_line(0, 0, 0, self.H, fill="white", dash=(3, 3),
                                                state="hidden")
        self._schedule()

    def _schedule(self):
        self.root.after(self.interval_ms, self.refresh)

    def refresh(self):
        samples = self.loop.latest_samples
        if samples is not None and len(samples) > 1:
            self.wave.coords(self.wave_line, *waveform_points(samples, self.W, self.H))
            self.fft.coords(self.fft_line,
                            *spectrum_points(samples, self.W, self.H, self.sample_rate))

        freq = self.app.last_freq
        if freq is not None:
            x = freq_to_x(freq, self.W)
            self.fft.coords(self.peak_marker, x, 0, x, self.H)
            self.fft.itemconfig(self.peak_marker, state="normal")
        else:
            self.fft.itemconfig(self.peak_marker, state="hidden")

        self.status.config(text=self.status_text())
        self._schedule()

    def status_text(self):
        app = self.app
        left, right = app.drive.outputs()
        cmd = app.last_command.name if app.last_command else "-"
        pitch = f"{app.last_freq:6.0f} Hz" if app.last_freq else "   --   "
        level = getattr(app, "last_rms", 0.0)
        loud = "LOUD" if level >= self.min_rms else "quiet"
        text = (f"Role {app.game.role.value.upper():6}  Phase {app.game.phase.value.upper():8}  "
                f"Pitch {pitch}  Last cmd {cmd:8}  Wheels L{left:+4d} R{right:+4d}\n"
                f"Level {level:5.0f} / threshold {self.min_rms:.0f} ({loud})")
        if self.loop.error:
            text += f"\nCONTROL LOOP STOPPED: {self.loop.error!r}"
        return text
