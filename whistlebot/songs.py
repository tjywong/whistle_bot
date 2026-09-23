"""Victory and defeat songs, rendered as 16-bit PCM for the speaker."""

import numpy as np

from .pitch import SAMPLE_RATE

# (frequency in Hz, seconds); frequency 0 is a rest.
VICTORY = [  # stadium "charge!" fanfare
    (392.00, 0.15), (523.25, 0.15), (659.25, 0.15), (783.99, 0.30),
    (0, 0.08), (659.25, 0.15), (783.99, 0.60),
]
DEFEAT = [  # sad trombone
    (293.66, 0.40), (277.18, 0.40), (261.63, 0.40), (246.94, 1.00),
]


def synthesize(song, sample_rate=SAMPLE_RATE, volume=0.5, fade_s=0.01):
    """Render a song to mono int16 PCM bytes."""
    pieces = []
    for freq, seconds in song:
        n = int(round(seconds * sample_rate))
        if freq <= 0:
            pieces.append(np.zeros(n))
            continue
        t = np.arange(n) / sample_rate
        tone = np.sin(2 * np.pi * freq * t)
        fade = min(int(fade_s * sample_rate), n // 2)
        if fade:  # ramp edges to avoid clicks between notes
            ramp = np.linspace(0.0, 1.0, fade)
            tone[:fade] *= ramp
            tone[-fade:] *= ramp[::-1]
        pieces.append(tone)
    wave = np.concatenate(pieces) if pieces else np.zeros(0)
    return (wave * volume * 32767).astype(np.int16).tobytes()
