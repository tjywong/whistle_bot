import pytest

from whistlebot.commands import Bands, Command, WhistleDecoder, classify


@pytest.mark.parametrize("freq, expected", [
    (None, None),
    (700, Command.STOP),
    (1200, Command.LEFT),
    (1800, Command.RIGHT),
    (2500, Command.SPEED_UP),
    (3500, Command.GOAL),
])
def test_classify(freq, expected):
    assert classify(freq) is expected


def test_range_low_is_inclusive_high_exclusive():
    b = Bands()
    assert classify(b.left[0]) is Command.LEFT
    assert classify(b.goal[0]) is Command.GOAL
    assert classify(b.goal[1]) is None


def test_pitch_outside_every_range_is_ignored():
    assert classify(400) is None     # below STOP: background rumble
    assert classify(4800) is None    # above GOAL


def test_gaps_between_ranges_are_ignored():
    b = Bands(stop=(600, 800), left=(1000, 1500))
    assert classify(900, b) is None


def test_any_order_of_ranges():
    b = Bands(stop=(3000, 3500), goal=(600, 900), left=(1000, 1400),
              right=(1500, 2000), speed_up=(2100, 2800)).validate()
    assert classify(3200, b) is Command.STOP
    assert classify(700, b) is Command.GOAL
    assert [c for c, _ in b.items()][0] is Command.GOAL


@pytest.mark.parametrize("bands", [
    Bands(stop=(1000, 900)),           # empty
    Bands(stop=(600, 1100)),           # overlaps LEFT
    Bands(goal=(3000, 6000)),          # beyond detector range
])
def test_invalid_bands_rejected(bands):
    with pytest.raises(ValueError):
        bands.validate()


def test_bands_dict_round_trip():
    b = Bands(stop=(650, 950))
    assert Bands.from_dict(b.to_dict()) == b


def feed_all(decoder, freqs):
    return [decoder.feed(f) for f in freqs]


def test_fires_once_after_hold():
    d = WhistleDecoder(hold_frames=3)
    out = feed_all(d, [2500] * 6)
    assert out == [None, None, Command.SPEED_UP, None, None, None]


def test_short_blip_is_ignored():
    d = WhistleDecoder(hold_frames=3)
    assert feed_all(d, [2500, 2500, None, 2500, 2500]) == [None] * 5


def test_new_whistle_after_gap_fires_again():
    d = WhistleDecoder(hold_frames=2)
    out = feed_all(d, [700, 700, None, 700, 700])
    assert out.count(Command.STOP) == 2


def test_changing_band_fires_new_command():
    d = WhistleDecoder(hold_frames=2)
    out = feed_all(d, [1200, 1200, 1800, 1800])
    assert out == [None, Command.LEFT, None, Command.RIGHT]


def test_goal_needs_long_hold():
    d = WhistleDecoder(hold_frames=2, goal_hold_frames=5)
    out = feed_all(d, [3500] * 5)
    assert out == [None, None, None, None, Command.GOAL]


def test_short_goal_band_whistle_does_nothing():
    d = WhistleDecoder(hold_frames=2, goal_hold_frames=5)
    assert feed_all(d, [3500] * 4 + [None]) == [None] * 5
