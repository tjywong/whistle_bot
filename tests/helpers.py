import numpy as np

from whistlebot.pitch import SAMPLE_RATE


def tone(freq, n=2048, amplitude=10000, sample_rate=SAMPLE_RATE):
    t = np.arange(n) / sample_rate
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.int16)


def silence(n=2048):
    return np.zeros(n, dtype=np.int16)


class FakeMotors:
    def __init__(self):
        self.calls = []

    def set_speeds(self, left, right):
        self.calls.append((left, right))

    @property
    def last(self):
        return self.calls[-1] if self.calls else None


class FakeLight:
    def __init__(self, level=50.0):
        self.level = level

    def read(self):
        return self.level
