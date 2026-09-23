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
    b = Bands(stop=(600, 800), backward=(1000, 1200))
    assert classify(900, b) is None


def test_any_order_of_ranges():
    b = Bands(stop=(3000, 3500), goal=(600, 700), backward=(750, 950),
              left=(1000, 1400), right=(1500, 2000), forward=(2050, 2150),
              speed_up=(2200, 2800)).validate()
    assert classify(3200, b) is Command.STOP
    assert classify(650, b) is Command.GOAL
    assert [c for c, _ in b.items()][0] is Command.GOAL


@pytest.mark.parametrize("bands", [
    Bands(stop=(1000, 900)),           # empty
    Bands(stop=(600, 1000)),           # overlaps BACKWARD
    Bands(goal=(3000, 6000)),          # beyond detector range
])
def test_invalid_bands_rejected(bands):
    with pytest.raises(ValueError):
        bands.validate()


def test_bands_dict_round_trip():
    b = Bands(stop=(650, 880))
    assert Bands.from_dict(b.to_dict()) == b


# A calibration saved before FORWARD/BACKWARD existed (the real one from
# calibration.json at that time).
LEGACY = {"stop": [714, 948], "left": [948, 1175], "right": [1175, 1461],
          "speed_up": [1510, 1956], "goal": [3000, 4500]}


def test_legacy_ranges_are_kept():
    b = Bands.from_dict(LEGACY).validate()
    assert b.stop == (714, 948) and b.speed_up == (1510, 1956)


def test_new_commands_fitted_into_largest_gap():
    b = Bands.from_dict(LEGACY).validate()
    # Largest free gap is 1956-3000 Hz; it is split between the two.
    assert 1956 <= b.forward[0] < b.forward[1] <= b.backward[0] < b.backward[1] <= 3000
    assert classify(sum(b.forward) / 2, b) is Command.FORWARD
    assert classify(sum(b.backward) / 2, b) is Command.BACKWARD


def test_no_room_for_new_commands_raises():
    full = {"stop": [600, 1500], "left": [1500, 2500], "right": [2500, 3500],
            "speed_up": [3500, 4000], "goal": [4000, 5000]}
    with pytest.raises(ValueError, match="no free"):
        Bands.from_dict(full)


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


def test_forward_and_backward_classified():
    assert classify(2000) is Command.FORWARD
    assert classify(1000) is Command.BACKWARD


def test_goal_needs_long_hold():
    d = WhistleDecoder(hold_frames=2, goal_hold_frames=5)
    out = feed_all(d, [3500] * 5)
    assert out == [None, None, None, None, Command.GOAL]


def test_short_goal_band_whistle_does_nothing():
    d = WhistleDecoder(hold_frames=2, goal_hold_frames=5)
    assert feed_all(d, [3500] * 4 + [None]) == [None] * 5
