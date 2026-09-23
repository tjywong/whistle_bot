import numpy as np
import pytest

from whistlebot.pitch import bytes_to_samples, dominant_frequency
from tests.helpers import silence, tone


@pytest.mark.parametrize("freq", [800, 1200, 1800, 2500, 3500])
def test_finds_whistle_pitch(freq):
    assert dominant_frequency(tone(freq)) == pytest.approx(freq, abs=25)


@pytest.mark.parametrize("freq", [712.3, 1003.7, 1234.5, 2718.2])
def test_pitch_is_accurate_between_fft_bins(freq):
    # Bins are ~21.5 Hz wide; interpolation should land within a few Hz.
    assert dominant_frequency(tone(freq)) == pytest.approx(freq, abs=3)


def test_silence_is_not_a_whistle():
    assert dominant_frequency(silence()) is None


def test_quiet_tone_is_ignored():
    assert dominant_frequency(tone(1500, amplitude=100)) is None


def test_broadband_noise_is_not_a_whistle():
    noise = np.random.default_rng(0).normal(0, 5000, 2048).astype(np.int16)
    assert dominant_frequency(noise) is None


def test_out_of_band_tone_is_ignored():
    assert dominant_frequency(tone(100)) is None


def test_empty_chunk():
    assert dominant_frequency(np.array([], dtype=np.int16)) is None


def test_bytes_to_samples_round_trip():
    samples = tone(1000, n=64)
    assert np.array_equal(bytes_to_samples(samples.tobytes()), samples)
