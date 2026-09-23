"""Whistle calibration: per-command pitch ranges and the noise threshold,
saved to JSON so they survive restarts."""

import json
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

import numpy as np

from .commands import Bands, Command
from .pitch import MAX_HZ, MIN_RMS, MIN_TONALITY, dominant_frequency, rms


@dataclass
class Calibration:
    bands: Bands = field(default_factory=Bands)
    min_rms: float = MIN_RMS
    min_tonality: float = MIN_TONALITY

    def detector(self):
        """dominant_frequency with this calibration's thresholds."""
        return partial(dominant_frequency, min_rms=self.min_rms,
                       min_tonality=self.min_tonality)

    def to_dict(self):
        return {"bands": self.bands.to_dict(), "min_rms": self.min_rms,
                "min_tonality": self.min_tonality}

    @classmethod
    def from_dict(cls, data):
        return cls(bands=Bands.from_dict(data.get("bands", {})).validate(),
                   min_rms=float(data.get("min_rms", MIN_RMS)),
                   min_tonality=float(data.get("min_tonality", MIN_TONALITY)))


def load(path):
    """Load a calibration, falling back to defaults if missing or invalid."""
    try:
        return Calibration.from_dict(json.loads(Path(path).read_text()))
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return Calibration()


def save(calibration, path):
    Path(path).write_text(json.dumps(calibration.to_dict(), indent=2) + "\n")


def median_pitch(freqs, min_count=5):
    """Median of the detected pitches, or None if too few were heard."""
    heard = [f for f in freqs if f is not None]
    if len(heard) < min_count:
        return None
    return float(np.median(heard))


def record_band(bands, cmd, center, width_frac=0.15, min_gap_hz=40.0):
    """Give ``cmd`` a range around the whistled ``center`` and trim any other
    command whose range it overlaps.

    The new range spans ±``width_frac`` but stops halfway to the other
    commands' centres, so each keeps its own whistle. Raises ValueError if
    ``center`` is within ``min_gap_hz`` of another command's centre.
    """
    low, high = center * (1 - width_frac), center * (1 + width_frac)
    for other, (o_low, o_high) in bands.items():
        if other is cmd:
            continue
        o_center = (o_low + o_high) / 2
        if abs(o_center - center) < min_gap_hz:
            raise ValueError(f"{center:.0f} Hz is too close to {other.name} "
                             f"({o_center:.0f} Hz); pick a more different pitch")
        if o_center < center:
            low = max(low, (o_center + center) / 2)
        else:
            high = min(high, (o_center + center) / 2)
    low, high = max(low, 0.0), min(high, MAX_HZ)

    result = bands.with_range(cmd, low, high)
    for other, (o_low, o_high) in bands.items():
        if other is cmd or o_high <= low or o_low >= high:
            continue
        if (o_low + o_high) / 2 < center:
            result = result.with_range(other, o_low, low)
        else:
            result = result.with_range(other, high, o_high)
    return result.validate()


def noise_threshold(rms_values, factor=3.0, floor=MIN_RMS):
    """Loudness threshold a comfortable margin above measured background noise."""
    if not len(rms_values):
        return floor
    return max(floor, factor * float(np.percentile(rms_values, 95)))


class PitchMonitor:
    """Minimal ``app`` for ControlLoop during calibration: tracks the live
    pitch and loudness, and records them on request."""

    def __init__(self, calibration):
        self.calibration = calibration
        self.last_freq = None
        self.last_rms = 0.0
        self._recording = None

    def step(self, samples):
        self.last_rms = rms(samples)
        self.last_freq = self.calibration.detector()(samples)
        if self._recording is not None:
            self._recording.append((self.last_rms, self.last_freq))

    def start_recording(self):
        self._recording = []

    def stop_recording(self):
        recorded, self._recording = self._recording or [], None
        return recorded
