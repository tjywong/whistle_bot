"""Turn whistle pitches into robot commands."""

from dataclasses import dataclass, fields, replace
from enum import Enum

from .pitch import MAX_HZ


class Command(Enum):
    STOP = "stop"
    LEFT = "left"
    RIGHT = "right"
    SPEED_UP = "speed_up"
    GOAL = "goal"


@dataclass(frozen=True)
class Bands:
    """(low, high) Hz range for each command; low is inclusive, high exclusive.

    Pitches that fall between ranges are ignored, so gaps help reject
    background noise. Field names match ``Command`` values.
    """
    stop: tuple = (600.0, 1000.0)
    left: tuple = (1000.0, 1500.0)
    right: tuple = (1500.0, 2200.0)
    speed_up: tuple = (2200.0, 3000.0)
    goal: tuple = (3000.0, 4500.0)

    def get(self, cmd):
        return getattr(self, cmd.value)

    def items(self):
        """[(Command, (low, high))] sorted by frequency."""
        return sorted(((c, self.get(c)) for c in Command), key=lambda item: item[1][0])

    def with_range(self, cmd, low, high):
        return replace(self, **{cmd.value: (float(low), float(high))})

    def validate(self):
        """Raise ValueError if any range is empty, out of bounds or overlapping."""
        for cmd, (low, high) in self.items():
            if not 0 <= low < high <= MAX_HZ:
                raise ValueError(f"{cmd.name}: need 0 ≤ low < high ≤ {MAX_HZ:.0f} Hz "
                                 f"(got {low:.0f}–{high:.0f})")
        ordered = self.items()
        for (a, (_, a_high)), (b, (b_low, _)) in zip(ordered, ordered[1:]):
            if a_high > b_low:
                raise ValueError(f"{a.name} and {b.name} ranges overlap")
        return self

    def to_dict(self):
        return {f.name: list(getattr(self, f.name)) for f in fields(self)}

    @classmethod
    def from_dict(cls, data):
        return cls(**{k: (float(v[0]), float(v[1])) for k, v in data.items()
                      if k in {f.name for f in fields(cls)}})


def classify(freq, bands=Bands()):
    """Map one frequency to a command (None for no whistle or a gap)."""
    if freq is None:
        return None
    for cmd, (low, high) in bands.items():
        if low <= freq < high:
            return cmd
    return None


class WhistleDecoder:
    """Debounce per-chunk pitches into one command per whistle.

    A command fires once after its band has been held for ``hold_frames``
    consecutive chunks. GOAL is the special command and needs a longer
    hold (``goal_hold_frames``) so a stray squeak can't end the game.
    """

    def __init__(self, bands=Bands(), hold_frames=4, goal_hold_frames=15):
        self.bands = bands
        self.hold_frames = hold_frames
        self.goal_hold_frames = goal_hold_frames
        self._current = None
        self._count = 0
        self._fired = False

    def feed(self, freq):
        cmd = classify(freq, self.bands)
        if cmd != self._current:
            self._current = cmd
            self._count = 0
            self._fired = False
        if cmd is None:
            return None

        self._count += 1
        needed = self.goal_hold_frames if cmd is Command.GOAL else self.hold_frames
        if not self._fired and self._count >= needed:
            self._fired = True
            return cmd
        return None
