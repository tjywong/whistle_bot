import numpy as np
import pytest

from whistlebot.pitch import dominant_frequency
from whistlebot.songs import DEFEAT, VICTORY, synthesize

SR = 44100


def samples(pcm):
    return np.frombuffer(pcm, dtype=np.int16)


@pytest.mark.parametrize("song", [VICTORY, DEFEAT])
def test_length_matches_song(song):
    expected = sum(int(round(s * SR)) for _, s in song)
    assert samples(synthesize(song, SR)).size == expected


def test_note_has_right_pitch():
    pcm = samples(synthesize([(440.0, 0.5)], SR))
    assert dominant_frequency(pcm[:8192], SR) == pytest.approx(440, abs=6)


def test_rest_is_silent():
    assert not samples(synthesize([(0, 0.1)], SR)).any()


def test_volume_limits_peak():
    pcm = samples(synthesize([(440.0, 0.2)], SR, volume=0.5))
    assert np.abs(pcm).max() <= 0.5 * 32767 + 1


def test_notes_fade_in_and_out():
    pcm = samples(synthesize([(440.0, 0.2)], SR))
    assert pcm[0] == 0 and abs(int(pcm[-1])) < 100


def test_victory_ends_higher_than_defeat():
    assert VICTORY[-1][0] > DEFEAT[-1][0]


def test_empty_song():
    assert synthesize([], SR) == b""
