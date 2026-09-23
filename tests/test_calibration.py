import json

import pytest

from whistlebot import calibration as cal
from whistlebot.commands import Bands, Command, classify
from whistlebot.pitch import dominant_frequency
from tests.helpers import silence, tone


def test_median_pitch_needs_enough_samples():
    assert cal.median_pitch([1000, None, 1010]) is None
    assert cal.median_pitch([1000, 1010, 990, None, 1005, 2000]) == 1005


def test_record_band_centres_on_whistle():
    b, moved = cal.record_band(Bands(), Command.RIGHT, 1700)
    lo, hi = b.right
    assert lo < 1700 < hi and moved == []
    assert classify(1700, b) is Command.RIGHT


def test_record_band_trims_overlapping_neighbour():
    # 1100 Hz is inside the default BACKWARD range; recording STOP there must
    # take it over and shrink its neighbours so they stay separate.
    b, _ = cal.record_band(Bands(), Command.STOP, 1100)
    assert classify(1100, b) is Command.STOP
    assert classify(1350, b) is Command.LEFT


def test_record_band_stops_at_log_midpoint_to_neighbour():
    b, _ = cal.record_band(Bands(), Command.LEFT, 1300)
    right_center = cal._centre(*Bands().right)
    assert b.left[1] == pytest.approx((1300 * right_center) ** 0.5)


def test_recorded_command_too_close_is_rejected():
    b, _ = cal.record_band(Bands(), Command.LEFT, 1000)
    with pytest.raises(ValueError, match="quarter tone"):
        cal.record_band(b, Command.RIGHT, 1010, fixed={Command.LEFT: 1000})


def test_unrecorded_command_in_the_way_is_moved():
    left_center = cal._centre(*Bands().left)
    b, moved = cal.record_band(Bands(), Command.STOP, left_center)
    assert moved == [Command.LEFT]
    assert classify(left_center, b) is Command.STOP
    assert b.left != Bands().left
    b.validate()


def notes(base, n):
    """n pitches, each a half step above the previous."""
    return [base * cal.HALF_STEP ** i for i in range(n)]


@pytest.mark.parametrize("base", [700, 1000, 1500, 2500])
def test_half_steps_get_separate_ranges(base):
    cmds = [Command.STOP, Command.LEFT, Command.RIGHT]
    b, fixed = Bands(), {}
    for cmd, f in zip(cmds, notes(base, 3)):
        b, _ = cal.record_band(b, cmd, f, fixed=fixed)
        fixed[cmd] = f
    for cmd, f in zip(cmds, notes(base, 3)):
        assert classify(f, b) is cmd


@pytest.mark.parametrize("base", [700, 1000, 2000])
def test_half_step_whistles_detected_end_to_end(base):
    """Synthesized whistles a half step apart come out as different commands."""
    lo_note, hi_note = notes(base, 2)
    b, _ = cal.record_band(Bands(), Command.LEFT, lo_note)
    b, _ = cal.record_band(b, Command.RIGHT, hi_note, fixed={Command.LEFT: lo_note})
    assert classify(dominant_frequency(tone(lo_note)), b) is Command.LEFT
    assert classify(dominant_frequency(tone(hi_note)), b) is Command.RIGHT


def test_record_every_command_in_any_order():
    whistles = [(Command.GOAL, 800), (Command.BACKWARD, 1100), (Command.LEFT, 1300),
                (Command.RIGHT, 1600), (Command.FORWARD, 1950), (Command.SLOW_DOWN, 2500),
                (Command.STOP, 3200)]
    b, fixed = Bands(), {}
    for cmd, f in whistles:
        b, _ = cal.record_band(b, cmd, f, fixed=fixed)
        fixed[cmd] = f
    for cmd, f in whistles:
        assert classify(f, b) is cmd


def test_seven_commands_in_consecutive_half_steps():
    cmds = list(Command)
    b, fixed = Bands(), {}
    for cmd, f in zip(cmds, notes(900, 7)):
        b, _ = cal.record_band(b, cmd, f, fixed=fixed)
        fixed[cmd] = f
    for cmd, f in zip(cmds, notes(900, 7)):
        assert classify(f, b) is cmd


def test_noise_threshold():
    assert cal.noise_threshold([]) == cal.MIN_RMS
    assert cal.noise_threshold([100, 120, 110]) == cal.MIN_RMS  # quiet room: floor
    assert cal.noise_threshold([900, 1000, 1000]) == pytest.approx(3000)


def test_save_and_load(tmp_path):
    path = tmp_path / "cal.json"
    c = cal.Calibration(bands=Bands(stop=(650, 880)), min_rms=3000)
    cal.save(c, path)
    assert cal.load(path) == c
    assert json.loads(path.read_text())["min_rms"] == 3000


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
