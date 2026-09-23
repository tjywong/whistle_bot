"""Background thread that runs the bot so the GUI can own the main thread."""

import threading


class ControlLoop(threading.Thread):
    """Reads audio chunks and feeds them to ``app.step`` until stopped.

    ``latest_samples`` always holds the most recent chunk for the HUD.
    Any exception is kept in ``error`` so the GUI can show it.
    """

    def __init__(self, app, read_samples):
        super().__init__(name="control", daemon=True)
        self.app = app
        self.read_samples = read_samples
        self.latest_samples = None
        self.error = None
        self._stop_event = threading.Event()

    def run(self):
        try:
            while not self._stop_event.is_set():
                samples = self.read_samples()
                self.latest_samples = samples
                self.app.step(samples)
        except Exception as exc:  # surfaced in the HUD
            self.error = exc

    def stop(self, timeout=3.0):
        self._stop_event.set()
        self.join(timeout)
