import tkinter as tk

import pytest

from whistlebot import calibration as cal
from whistlebot.calibration_ui import CalibrationWindow
from whistlebot.commands import Bands, Command


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    r.withdraw()
    yield r
    r.destroy()


def make(root):
    monitor = cal.PitchMonitor(cal.Calibration())
    return CalibrationWindow(root, cal.Calibration(), monitor), monitor


def fake_recording(monitor, freqs):
    monitor.start_recording()
    monitor._recording.extend((5000.0, f) for f in freqs)


def test_record_updates_range(root):
    w, monitor = make(root)
    fake_recording(monitor, [1850] * 10)
    w._finish_record(Command.RIGHT)
    lo, hi = float(w.low[Command.RIGHT].get()), float(w.high[Command.RIGHT].get())
    assert lo < 1850 < hi
    assert "1850" in w.heard[Command.RIGHT].cget("text")


def test_record_with_no_whistle_shows_error(root):
    w, monitor = make(root)
    fake_recording(monitor, [None] * 10)
    w._finish_record(Command.STOP)
    assert "Didn't hear" in w.msg.cget("text")
    assert w.low[Command.STOP].get() == f"{Bands().stop[0]:.0f}"


def test_measure_noise_sets_threshold(root):
    w, monitor = make(root)
    monitor.start_recording()
    monitor._recording.extend((1000.0, None) for _ in range(10))
    w._finish_noise()
    assert float(w.min_rms.get()) == pytest.approx(3000)


def test_save_with_typed_values(root):
    w, _ = make(root)
    w.low[Command.STOP].set("650")
    w.high[Command.STOP].set("900")
    w.min_rms.set("2500")
    w._save()
    assert w.result.bands.stop == (650.0, 900.0) and w.result.min_rms == 2500


def test_save_rejects_overlap(root):
    w, _ = make(root)
    w.high[Command.STOP].set("1200")  # runs into LEFT
    w._save()
    assert w.result is None and "overlap" in w.msg.cget("text")
