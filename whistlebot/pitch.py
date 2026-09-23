"""Find the pitch of a whistle in a chunk of microphone samples."""

import numpy as np

SAMPLE_RATE = 44100
MIN_HZ = 300.0
MAX_HZ = 5000.0

# Defaults tuned to ignore room noise; calibration can raise MIN_RMS further.
MIN_RMS = 2500.0      # loudness (int16 RMS) a chunk needs to count as a whistle
MIN_TONALITY = 15.0   # spectral peak / band average; whistles are very pure tones


def bytes_to_samples(data):
    """Convert a raw 16-bit mono PyAudio buffer to a numpy array."""
    return np.frombuffer(data, dtype=np.int16)


def rms(samples):
    x = np.asarray(samples, dtype=np.float64)
    return float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0


def dominant_frequency(samples, sample_rate=SAMPLE_RATE, min_hz=MIN_HZ,
                       max_hz=MAX_HZ, min_rms=MIN_RMS, min_tonality=MIN_TONALITY):
    """Return the whistle frequency in Hz, or None if there is no whistle.

    A chunk counts as a whistle when it is loud enough (``min_rms``) and
    tonal: the spectral peak must stand ``min_tonality`` times above the
    average level, which rejects talking, clapping and background noise.
    """
    x = np.asarray(samples, dtype=np.float64)
    if x.size == 0:
        return None
    if rms(x) < min_rms:
        return None

    spectrum = np.abs(np.fft.rfft(x * np.hanning(x.size)))
    freqs = np.fft.rfftfreq(x.size, 1.0 / sample_rate)
    band = (freqs >= min_hz) & (freqs <= max_hz)
    if not band.any():
        return None

    in_band = spectrum[band]
    peak = int(np.argmax(in_band))
    if in_band[peak] < min_tonality * np.mean(in_band):
        return None
    # A louder sound outside the band (hum, bass) means this isn't a whistle.
    if in_band[peak] < 0.5 * spectrum.max():
        return None
    return _refine_peak(spectrum, int(np.flatnonzero(band)[peak]), sample_rate / x.size)


def _refine_peak(spectrum, k, bin_hz):
    """Sub-bin peak frequency by fitting a parabola through the log
    magnitudes around bin ``k``. Bins are ~21 Hz wide, too coarse to tell
    half steps apart at low pitches; this gets within a few Hz."""
    if 0 < k < len(spectrum) - 1:
        a, b, c = np.log(spectrum[k - 1:k + 2] + 1e-12)
        denom = a - 2 * b + c
        if denom < 0:
            return float((k + 0.5 * (a - c) / denom) * bin_hz)
    return float(k * bin_hz)
