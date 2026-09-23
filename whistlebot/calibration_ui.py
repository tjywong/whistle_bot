"""Calibration window: record or type each command's whistle range."""

import tkinter as tk
from dataclasses import replace
from tkinter import ttk

from .calibration import Calibration, median_pitch, noise_threshold, record_band
from .commands import Bands, Command

RECORD_MS = 1500
NOISE_MS = 2000
LABELS = {
    Command.STOP: "Stop",
    Command.FORWARD: "Forward",
    Command.BACKWARD: "Backward",
    Command.LEFT: "Turn left",
    Command.RIGHT: "Turn right",
    Command.SPEED_UP: "Speed up",
    Command.GOAL: "GOAL (hold long)",
}


class CalibrationWindow:
    """Modal dialog. ``show()`` returns the new Calibration, or None if cancelled.

    ``monitor`` is a running PitchMonitor fed from the microphone.
    """

    def __init__(self, root, calibration, monitor):
        self.root = root
        self.monitor = monitor
        self.cal = replace(calibration)
        self.monitor.calibration = self.cal
        self.result = None
        self._busy = False
        self.recorded = {}  # command -> pitch recorded this session (kept in place)

        self.win = tk.Toplevel(root)
        self.win.title("whistle_bot: calibrate whistle")
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)
        f = ttk.Frame(self.win, padding=16)
        f.grid()

        ttk.Label(f, text="Press Record, then whistle that command steadily for "
                          f"{RECORD_MS / 1000:.1f} s.\nOr type your own ranges in Hz.",
                  justify="left").grid(row=0, column=0, columnspan=5, sticky="w")
        self.live = ttk.Label(f, text="", font=("Menlo", 13))
        self.live.grid(row=1, column=0, columnspan=5, sticky="w", pady=(8, 8))

        for col, text in enumerate(["Command", "Low Hz", "High Hz", "", "Heard"]):
            ttk.Label(f, text=text, foreground="gray").grid(row=2, column=col, sticky="w")
        self.low, self.high, self.heard = {}, {}, {}
        for row, cmd in enumerate(Command, start=3):
            lo, hi = self.cal.bands.get(cmd)
            self.low[cmd] = tk.StringVar(value=f"{lo:.0f}")
            self.high[cmd] = tk.StringVar(value=f"{hi:.0f}")
            self.heard[cmd] = ttk.Label(f, text="", width=18)
            ttk.Label(f, text=LABELS[cmd]).grid(row=row, column=0, sticky="w", padx=(0, 8))
            ttk.Entry(f, textvariable=self.low[cmd], width=7).grid(row=row, column=1)
            ttk.Entry(f, textvariable=self.high[cmd], width=7).grid(row=row, column=2)
            ttk.Button(f, text="Record", command=lambda c=cmd: self._record(c)).grid(
                row=row, column=3, padx=6)
            self.heard[cmd].grid(row=row, column=4, sticky="w")

        n = len(Command) + 3
        ttk.Separator(f).grid(row=n, columnspan=5, sticky="ew", pady=8)
        ttk.Label(f, text="Min loudness (RMS)").grid(row=n + 1, column=0, sticky="w")
        self.min_rms = tk.StringVar(value=f"{self.cal.min_rms:.0f}")
        ttk.Entry(f, textvariable=self.min_rms, width=7).grid(row=n + 1, column=1)
        ttk.Button(f, text="Measure noise", command=self._measure_noise).grid(
            row=n + 1, column=2, columnspan=2, sticky="w", padx=6)
        ttk.Label(f, text="(stay quiet while it listens)", foreground="gray").grid(
            row=n + 1, column=4, sticky="w")

        self.msg = ttk.Label(f, text="", foreground="red", wraplength=460)
        self.msg.grid(row=n + 2, columnspan=5, sticky="w", pady=(8, 0))
        buttons = ttk.Frame(f)
        buttons.grid(row=n + 3, columnspan=5, sticky="e", pady=(8, 0))
        ttk.Button(buttons, text="Reset defaults", command=self._defaults).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=self.win.destroy).pack(side="left", padx=6)
        ttk.Button(buttons, text="Save", command=self._save).pack(side="left")
        self._tick()

    # --- helpers -----------------------------------------------------------

    def _say(self, text, colour="red"):
        self.msg.config(text=text, foreground=colour)

    def _bands_from_entries(self):
        bands = Bands()
        for cmd in Command:
            try:
                lo, hi = float(self.low[cmd].get()), float(self.high[cmd].get())
            except ValueError:
                raise ValueError(f"{LABELS[cmd]}: ranges must be numbers") from None
            bands = bands.with_range(cmd, lo, hi)
        return bands.validate()

    def _show_bands(self, bands):
        for cmd in Command:
            lo, hi = bands.get(cmd)
            self.low[cmd].set(f"{lo:.0f}")
            self.high[cmd].set(f"{hi:.0f}")

    def _tick(self):
        if not self.win.winfo_exists():
            return
        f = self.monitor.last_freq
        pitch = f"{f:5.0f} Hz" if f else "   --   "
        self.live.config(text=f"Hearing: {pitch}   level {self.monitor.last_rms:5.0f}"
                              f" / threshold {self.cal.min_rms:.0f}")
        self.win.after(100, self._tick)

    # --- actions -----------------------------------------------------------

    def _record(self, cmd):
        if self._busy:
            return
        self._busy = True
        self._say(f"Whistle {LABELS[cmd]} now…", "blue")
        self.monitor.start_recording()
        self.win.after(RECORD_MS, lambda: self._finish_record(cmd))

    def _finish_record(self, cmd):
        self._busy = False
        center = median_pitch(f for _, f in self.monitor.stop_recording())
        if center is None:
            self._say("Didn't hear a steady whistle. Whistle louder/closer, "
                      "or lower Min loudness.")
            return
        try:
            bands, moved = record_band(self._bands_from_entries(), cmd, center,
                                       fixed={c: f for c, f in self.recorded.items()
                                              if c is not cmd})
        except ValueError as exc:
            self._say(str(exc))
            return
        self._show_bands(bands)
        self.recorded[cmd] = center
        self.heard[cmd].config(text=f"{center:.0f} Hz")
        for other in moved:
            self.recorded.pop(other, None)
            self.heard[other].config(text="moved: record it")
        note = (f" Moved {', '.join(LABELS[m] for m in moved)} out of the way; "
                "record it too." if moved else "")
        self._say(f"{LABELS[cmd]} set to {center:.0f} Hz.{note}", "green")

    def _measure_noise(self):
        if self._busy:
            return
        self._busy = True
        self._say("Measuring background noise; stay quiet…", "blue")
        self.monitor.start_recording()
        self.win.after(NOISE_MS, self._finish_noise)

    def _finish_noise(self):
        self._busy = False
        threshold = noise_threshold([r for r, _ in self.monitor.stop_recording()])
        self.min_rms.set(f"{threshold:.0f}")
        self.cal.min_rms = threshold
        self._say(f"Min loudness set to {threshold:.0f}.", "green")

    def _defaults(self):
        self._show_bands(Bands())
        self.min_rms.set(f"{Calibration().min_rms:.0f}")
        self.recorded.clear()
        for label in self.heard.values():
            label.config(text="")

    def _save(self):
        try:
            bands = self._bands_from_entries()
            min_rms = float(self.min_rms.get())
            if min_rms <= 0:
                raise ValueError("Min loudness must be positive")
        except ValueError as exc:
            self._say(str(exc))
            return
        self.result = replace(self.cal, bands=bands, min_rms=min_rms)
        self.win.destroy()

    def show(self):
        self.win.grab_set()
        self.win.lift()
        self.win.focus_force()
        self.root.wait_window(self.win)
        return self.result
