import tkinter as tk
from types import SimpleNamespace

import numpy as np
import pytest

from whistlebot.commands import Bands, Command
from whistlebot.drive import Drive
from whistlebot.game import Game, Role
from whistlebot.hud import (MAX_HZ, Hud, band_regions, db_to_y, freq_to_x,
                            spectrum_db, spectrum_points, waveform_points)
from tests.helpers import FakeMotors, silence, tone


def pairs(flat):
    return np.array(flat).reshape(-1, 2)


def test_waveform_fits_canvas():
    pts = pairs(waveform_points(tone(1000, amplitude=32767), 300, 100))
    assert len(pts) == 300
    assert pts[:, 0].min() == 0 and pts[:, 0].max() == 300
    assert pts[:, 1].min() >= 0 and pts[:, 1].max() <= 100


def test_silent_waveform_is_centre_line():
    assert set(pairs(waveform_points(silence(), 300, 100))[:, 1]) == {50}


def test_spectrum_peak_at_tone():
    freqs, db = spectrum_db(tone(2000, amplitude=16384))
    assert freqs[np.argmax(db)] == pytest.approx(2000, abs=25)
    assert db.max() == pytest.approx(-6, abs=1.5)  # half scale = -6 dBFS


def test_spectrum_points_stay_in_range():
    pts = pairs(spectrum_points(tone(2000), 500, 200))
    assert pts[:, 0].max() <= 500
    assert pts[:, 1].min() >= 0 and pts[:, 1].max() <= 200


def test_peak_is_highest_point_on_screen():
    pts = pairs(spectrum_points(tone(2000), 500, 200))
    assert pts[np.argmin(pts[:, 1]), 0] == pytest.approx(freq_to_x(2000, 500), abs=3)


def test_scales():
    assert freq_to_x(MAX_HZ / 2, 400) == 200
    assert db_to_y(0, 200) == 0 and db_to_y(-100, 200) == 200 and db_to_y(-500, 200) == 200


def test_band_regions_cover_bands_in_order():
    regions = band_regions(Bands())
    assert [r[0] for r in regions] == ["STOP", "BACK", "LEFT", "RIGHT", "FWD", "FASTER", "GOAL"]
    for (_, _, hi, _), (_, lo, _, _) in zip(regions, regions[1:]):
        assert hi == lo


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    r.withdraw()
    yield r
    r.destroy()


def test_hud_refresh_smoke(root):
    app = SimpleNamespace(game=Game(Role.BALL), drive=Drive(FakeMotors()),
                          last_freq=2000.0, last_command=Command.SPEED_UP)
    loop = SimpleNamespace(latest_samples=tone(2000), error=None)
    hud = Hud(root, app, loop, "Test Mic")
    hud.refresh()
    text = hud.status.cget("text")
    assert "BALL" in text and "2000 Hz" in text and "SPEED_UP" in text
    assert "MQTT: nothing heard yet" in text
    assert len(hud.fft.coords(hud.fft_line)) > 100


def test_hud_shows_loop_error(root):
    app = SimpleNamespace(game=Game(Role.GOALIE), drive=Drive(FakeMotors()),
                          last_freq=None, last_command=None)
    loop = SimpleNamespace(latest_samples=None, error=OSError("mic gone"))
    hud = Hud(root, app, loop, "Test Mic")
    hud.refresh()
    assert "mic gone" in hud.status.cget("text")
