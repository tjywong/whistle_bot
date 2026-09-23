"""Referee window: send start / ball_caught / ball_scored and watch the topic.

Stands in for the referee and the opponent so a single robot can be tested
alone. Run it with ``python MQTT.py --broker <host> --test-topic referee``.
"""

import queue
import time
import tkinter as tk
from tkinter import ttk

import MQTT

from .keys import bind_quit

POLL_MS = 100


class Referee:
    """``make_link(on_payload)`` returns a started-or-startable MqttLink-like
    object (``publish``, ``start``, ``stop``, ``connected``, ``topic``)."""

    def __init__(self, root, make_link, broker="", clock=time.strftime):
        self.root = root
        self.clock = clock
        self.inbox = queue.Queue()  # filled from the MQTT thread
        self.link = make_link(self.inbox.put)
        self.topic = self.link.topic
        self.broker = broker

        root.title(f"whistle_bot referee: {self.topic}")
        frame = ttk.Frame(root, padding=12)
        frame.pack(fill="both", expand=True)

        if self.topic == MQTT.TOPIC:
            tk.Label(frame, text=f"LIVE CLASS TOPIC: every robot on {MQTT.TOPIC} hears this. "
                                 "Use --test-topic for solo testing.",
                     bg="#b00020", fg="white", wraplength=460, justify="left",
                     padx=8, pady=4).pack(fill="x", pady=(0, 8))

        self.status = ttk.Label(frame, text="")
        self.status.pack(anchor="w")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=8)
        for text, payload in [("▶  Start", MQTT.START),
                              ("🧤  Ball caught", MQTT.BALL_CAUGHT),
                              ("⚽  Ball scored", MQTT.BALL_SCORED)]:
            ttk.Button(buttons, text=text, command=lambda p=payload: self.send(p)).pack(
                side="left", expand=True, fill="x", padx=2, ipady=6)

        custom = ttk.Frame(frame)
        custom.pack(fill="x")
        ttk.Label(custom, text="Custom message:").pack(side="left")
        self.custom = tk.StringVar()
        entry = ttk.Entry(custom, textvariable=self.custom)
        entry.pack(side="left", expand=True, fill="x", padx=4)
        entry.bind("<Return>", lambda e: self.send_custom())
        ttk.Button(custom, text="Send", command=self.send_custom).pack(side="left")

        log_frame = ttk.Frame(frame)
        log_frame.pack(fill="both", expand=True, pady=(8, 0))
        self.log = tk.Text(log_frame, height=16, width=60, state="disabled",
                           font=("Menlo", 12), bg="#111", fg="#ddd")
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.log.tag_configure("sent", foreground="#6cf")
        self.log.tag_configure("heard", foreground="#fc6")
        self.log.tag_configure("info", foreground="#888")

        bottom = ttk.Frame(frame)
        bottom.pack(fill="x", pady=(6, 0))
        ttk.Label(bottom, text="→ sent by this window    ← heard on the topic    "
                               "(q to quit)", foreground="gray").pack(side="left")
        ttk.Button(bottom, text="Clear log", command=self.clear).pack(side="right")

        root.protocol("WM_DELETE_WINDOW", self.close)
        bind_quit(root, self.close)
        self._write(f"topic {self.topic}", "info")
        self._poll()

    # --- actions -----------------------------------------------------------

    def send(self, payload):
        self.link.publish(payload)
        self._write(f"→ {payload}", "sent")

    def send_custom(self):
        payload = self.custom.get().strip()
        if payload:
            self.send(payload)
            self.custom.set("")

    def clear(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def close(self):
        try:
            self.link.stop()
        finally:
            self.root.destroy()

    # --- display -----------------------------------------------------------

    def log_text(self):
        return self.log.get("1.0", "end").strip()

    def _write(self, text, tag):
        self.log.configure(state="normal")
        self.log.insert("end", f"{self.clock('%H:%M:%S')}  {text}\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _poll(self):
        while True:
            try:
                payload = self.inbox.get_nowait()
            except queue.Empty:
                break
            self._write(f"← {payload}", "heard")
        dot = "● connected" if getattr(self.link, "connected", False) else "○ connecting…"
        self.status.config(text=f"{self.broker}  ·  {self.topic}  ·  {dot}")
        self.root.after(POLL_MS, self._poll)


def run(broker, port=1883, topic=MQTT.TEST_TOPIC):
    root = tk.Tk()

    def make_link(on_payload):
        link = MQTT.MqttLink(broker, on_payload, port=port, topic=topic)
        link.start()
        return link

    Referee(root, make_link, broker=f"{broker}:{port}")
    root.mainloop()
