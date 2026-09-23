import json

import pytest

from whistlebot import calibration as cal
from whistlebot.commands import Bands, Command, classify
from tests.helpers import silence, tone


def test_median_pitch_needs_enough_samples():
    assert cal.median_pitch([1000, None, 1010]) is None
    assert cal.median_pitch([1000, 1010, 990, None, 1005, 2000]) == 1005


def test_record_band_centres_on_whistle():
    b = cal.record_band(Bands(), Command.RIGHT, 1800)
    lo, hi = b.right
    assert lo < 1800 < hi
    assert classify(1800, b) is Command.RIGHT


def test_record_band_trims_overlapping_neighbour():
    # 1100 Hz is inside the default LEFT range; recording STOP there must
    # take it over and shrink LEFT so the two stay separate.
    b = cal.record_band(Bands(), Command.STOP, 1100)
    assert classify(1100, b) is Command.STOP
    assert classify(1300, b) is Command.LEFT
    b.validate()


def test_record_band_stops_halfway_to_neighbour_centre():
    b = Bands(left=(1000, 1200), right=(1500, 2200))
    b = cal.record_band(b, Command.LEFT, 1100)
    assert b.left[1] <= (1100 + 1850) / 2


def test_record_band_too_close_to_other_command():
    with pytest.raises(ValueError, match="too close"):
        cal.record_band(Bands(), Command.STOP, 1250)  # LEFT's centre


def test_record_every_command_in_any_order():
    b = Bands()
    for cmd, f in [(Command.GOAL, 900), (Command.STOP, 3200), (Command.LEFT, 1300),
                   (Command.RIGHT, 1900), (Command.SPEED_UP, 2500)]:
        b = cal.record_band(b, cmd, f)
    for cmd, f in [(Command.GOAL, 900), (Command.STOP, 3200), (Command.LEFT, 1300),
                   (Command.RIGHT, 1900), (Command.SPEED_UP, 2500)]:
        assert classify(f, b) is cmd


def test_noise_threshold():
    assert cal.noise_threshold([]) == cal.MIN_RMS
    assert cal.noise_threshold([100, 120, 110]) == cal.MIN_RMS  # quiet room: floor
    assert cal.noise_threshold([900, 1000, 1000]) == pytest.approx(3000)


def test_save_and_load(tmp_path):
    path = tmp_path / "cal.json"
    c = cal.Calibration(bands=Bands(stop=(650, 950)), min_rms=2500)
    cal.save(c, path)
    assert cal.load(path) == c
    assert json.loads(path.read_text())["min_rms"] == 2500


def test_load_missing_or_bad_file_gives_defaults(tmp_path):
    assert cal.load(tmp_path / "nope.json") == cal.Calibration()
    bad = tmp_path / "bad.json"
    bad.write_text('{"bands": {"stop": [2000, 100]}}')
    assert cal.load(bad) == cal.Calibration()


def test_detector_uses_threshold():
    loud_enough = cal.Calibration(min_rms=1000).detector()
    too_strict = cal.Calibration(min_rms=20000).detector()
    assert loud_enough(tone(1500)) == pytest.approx(1500, abs=25)
    assert too_strict(tone(1500)) is None


def test_pitch_monitor_records():
    m = cal.PitchMonitor(cal.Calibration())
    m.step(tone(1500))
    assert m.last_freq == pytest.approx(1500, abs=25)
    m.start_recording()
    m.step(tone(2000))
    m.step(silence())
    rec = m.stop_recording()
    assert len(rec) == 2 and rec[1] == (0.0, None)
    assert m.stop_recording() == []
