"""Whistle calibration: per-command pitch ranges and the noise threshold,
saved to JSON so they survive restarts."""

import json
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

import numpy as np

from .commands import Bands, Command, fit_into_gap
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


HALF_STEP = 2 ** (1 / 12)     # ~5.9% higher
QUARTER_TONE = 2 ** (1 / 24)  # ~2.9%: the closest two recorded whistles may be


def _centre(low, high):
    return (low * high) ** 0.5  # geometric: pitch is perceived on a log scale


def record_band(bands, cmd, center, fixed=None, width_frac=0.15,
                min_ratio=QUARTER_TONE):
    """Give ``cmd`` a range around the whistled ``center``.

    The range spans ±``width_frac`` but stops at the (log-scale) midpoint
    to every other command's pitch, so whistles a half step apart each
    get their own range. ``fixed`` maps already-recorded commands to the
    pitch actually whistled; those must be at least ``min_ratio`` away or
    ValueError is raised. Any other command that close is moved into free
    space instead. Overlapped neighbours are trimmed.

    Returns (new Bands, list of commands that were moved).
    """
    fixed = fixed or {}
    low, high = center * (1 - width_frac), center * (1 + width_frac)
    moved = []
    others = [(c, r) for c, r in bands.items() if c is not cmd]
    pitch_of = {c: fixed.get(c) or _centre(*r) for c, r in others}
    for other, _ in others:
        o_center = pitch_of[other]
        ratio = max(o_center, center) / min(o_center, center)
        if ratio < min_ratio:
            if other in fixed:
                raise ValueError(f"{center:.0f} Hz is within a quarter tone of "
                                 f"{other.name} ({o_center:.0f} Hz); pick a different pitch")
            moved.append(other)
            continue
        mid = _centre(o_center, center)
        if o_center < center:
            low = max(low, mid)
        else:
            high = min(high, mid)
    low, high = max(low, 0.0), min(high, MAX_HZ)

    result = bands.with_range(cmd, low, high)
    for other, (o_low, o_high) in others:
        if other in moved or o_high <= low or o_low >= high:
            continue
        if pitch_of[other] < center:
            result = result.with_range(other, o_low, low)
        else:
            result = result.with_range(other, high, o_high)
    if moved:
        result = fit_into_gap(result, moved)
    return result.validate(), moved


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
