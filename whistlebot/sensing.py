"""Detect the goalie reaching the ball's light sensor."""


class LightGuard:
    """Trips when the light reading moves ``delta`` away from its baseline.

    The first reading after ``reset()`` becomes the baseline, so this works
    whether the goalie shades the sensor or shines a light on it. The
    change must last ``trip_frames`` readings in a row to count.
    """

    def __init__(self, delta=15.0, trip_frames=3):
        self.delta = delta
        self.trip_frames = trip_frames
        self.reset()

    def reset(self):
        self.baseline = None
        self._count = 0
        self.tripped = False

    def update(self, reading):
        """Feed one reading; returns True only on the reading that trips."""
        if self.tripped or reading is None:
            return False
        if self.baseline is None:
            self.baseline = reading
            return False
        if abs(reading - self.baseline) >= self.delta:
            self._count += 1
        else:
            self._count = 0
        if self._count >= self.trip_frames:
            self.tripped = True
            return True
        return False
