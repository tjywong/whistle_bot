"""Startup popup for choosing the ball or goalie role."""

import tkinter as tk
from tkinter import ttk

from .game import Role
from .hardware import parse_card


def validate_choice(role, card_text, need_sensor=True):
    """Return (Role, sensor_card or None), or raise ValueError with a message."""
    role = Role(role)
    card_text = card_text.strip()
    if role is Role.GOALIE or not need_sensor:
        return role, parse_card(card_text) if card_text else None
    if not card_text:
        raise ValueError("The ball needs its Color Sensor card (e.g. red:1234).")
    return role, parse_card(card_text)


class RolePicker:
    """Modal dialog. ``show()`` returns (Role, sensor_card) or None if closed.

    ``connect_sensor`` is called with the card after the ball is chosen; if
    it raises, the error is shown and the user can fix the card and retry.
    ``on_calibrate`` opens the calibration window and returns a short
    summary to display (or None if nothing changed).
    """

    def __init__(self, root, status, sensor_card=None, need_sensor=True,
                 connect_sensor=None, on_calibrate=None, calibration_text=""):
        self.root = root
        self.need_sensor = need_sensor
        self.connect_sensor = connect_sensor
        self.on_calibrate = on_calibrate
        self.result = None

        self.win = tk.Toplevel(root)
        self.win.title("whistle_bot: choose role")
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)

        frame = ttk.Frame(self.win, padding=16)
        frame.grid()
        ttk.Label(frame, text=status, foreground="green").grid(columnspan=2, sticky="w")
        ttk.Label(frame, text="Which role is this robot playing?",
                  font=("TkDefaultFont", 14, "bold")).grid(columnspan=2, pady=(8, 12))

        ttk.Label(frame, text="Ball's Color Sensor card:").grid(row=2, column=0, sticky="w")
        self.card = tk.StringVar(value=f"{sensor_card[0]}:{sensor_card[1]}" if sensor_card else "")
        ttk.Entry(frame, textvariable=self.card, width=14).grid(row=2, column=1, sticky="w")

        ttk.Button(frame, text="⚽  Ball", command=lambda: self._pick(Role.BALL)).grid(
            row=3, column=0, pady=(12, 0), ipadx=12, ipady=6)
        ttk.Button(frame, text="🧤  Goalie", command=lambda: self._pick(Role.GOALIE)).grid(
            row=3, column=1, pady=(12, 0), ipadx=12, ipady=6)

        ttk.Button(frame, text="🎚  Calibrate whistle…", command=self._calibrate).grid(
            row=4, columnspan=2, pady=(10, 0), sticky="ew")
        self.cal_label = ttk.Label(frame, text=calibration_text, foreground="gray",
                                   wraplength=320, justify="left")
        self.cal_label.grid(row=5, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(frame, text="Press q to quit", foreground="gray").grid(
            row=6, columnspan=2, pady=(6, 0))

        self.error = ttk.Label(frame, text="", foreground="red", wraplength=320)
        self.error.grid(row=7, columnspan=2, pady=(8, 0))

    def _calibrate(self):
        if not self.on_calibrate:
            return
        self.win.grab_release()
        try:
            summary = self.on_calibrate()
        except Exception as exc:
            self.error.config(text=f"Calibration failed: {exc}", foreground="red")
            summary = None
        if self.win.winfo_exists():
            self.win.grab_set()
            if summary:
                self.cal_label.config(text=summary)

    def _pick(self, role):
        try:
            role, card = validate_choice(role, self.card.get(), self.need_sensor)
            if role is Role.BALL and self.connect_sensor and card:
                self.error.config(text="Connecting to Color Sensor…", foreground="gray")
                self.win.update_idletasks()
                self.connect_sensor(card)
        except Exception as exc:
            self.error.config(text=str(exc), foreground="red")
            return
        self.result = (role, card)
        self.win.destroy()

    def show(self):
        self.win.grab_set()
        self.win.lift()
        self.win.focus_force()
        self.root.wait_window(self.win)
        return self.result
