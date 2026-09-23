"""Robot hardware interfaces and adapters.

Everything else talks to ``Motors`` and ``LightSensor``, so tests can use
fakes and the LEGO wiring lives only here.
"""

from typing import Protocol


class Motors(Protocol):
    def set_speeds(self, left: int, right: int) -> None:
        """Set wheel speeds as percent, -100..100."""


class LightSensor(Protocol):
    def read(self) -> float:
        """Return the current light level (any consistent scale)."""


MOTOR_CARD = ("blue", "3685")  # Connection Card tapped on our Double Motor


def parse_card(text):
    """Parse "blue:3685" into ("blue", "3685")."""
    color, _, serial = text.partition(":")
    if not color or not serial:
        raise ValueError(f"card must look like color:serial, got {text!r}")
    return color.lower(), serial


def _connect(device, card):
    import legoeducation as le
    color, serial = card
    card_color = getattr(le, f"LEGO_COLOR_{color.upper()}", None)
    if card_color is None:
        raise ValueError(f"unknown LEGO card color {color!r}")
    device.connect(card_color=card_color, card_serial=serial)
    if not device.connected:
        raise RuntimeError(f"could not connect to {device.search_name} "
                           f"with card {color} {serial}; tap it with the card and retry")
    return device


class LegoDoubleMotor:
    """LEGO Education Double Motor: one unit driving the left and right wheels.

    The two sides face opposite ways, so "forward" is counter-clockwise on
    one output and clockwise on the other. ``left_reversed`` /
    ``right_reversed`` refer to the motor's LEFT / RIGHT outputs: flip them
    if the car drives backwards. ``swap_sides`` means the motor's LEFT
    output drives the car's right wheel (and vice versa): flip it if
    forward is right but turns are mirrored. Pass ``device`` to inject a
    fake in tests.
    """

    def __init__(self, card=MOTOR_CARD, left_reversed=False, right_reversed=True,
                 swap_sides=True, device=None):
        import legoeducation as le
        self._le = le
        self.reversed = {le.MOTOR_LEFT: left_reversed, le.MOTOR_RIGHT: right_reversed}
        # Which motor output drives the car's left / right wheel.
        self.left_wheel = le.MOTOR_RIGHT if swap_sides else le.MOTOR_LEFT
        self.right_wheel = le.MOTOR_LEFT if swap_sides else le.MOTOR_RIGHT
        self.device = device or _connect(le.DoubleMotor(), card)

    def set_speeds(self, left, right):
        """Car wheel speeds: ``left`` for the car's left wheel, ``right`` for its right."""
        le = self._le
        if left == 0 and right == 0:
            self.device.motor_stop(motor=le.MOTOR_BOTH)
            return
        self._run(self.left_wheel, left)
        self._run(self.right_wheel, right)

    def _run(self, motor, speed):
        le = self._le
        if speed == 0:
            self.device.motor_stop(motor=motor)
            return
        forward = (speed > 0) != self.reversed[motor]
        direction = (le.MOTOR_MOVE_DIRECTION_CLOCKWISE if forward
                     else le.MOTOR_MOVE_DIRECTION_COUNTERCLOCKWISE)
        self.device.motor_run(direction=direction, motor=motor,
                              speed=min(abs(int(speed)), 100))

    def close(self):
        self.set_speeds(0, 0)
        self.device.disconnect()


class LegoLightSensor:
    """LEGO Education Color Sensor mounted open at the front of the ball car.

    Reads reflection (0-100). Returns None until the sensor has sent its
    first reading.
    """

    def __init__(self, card, device=None):
        import legoeducation as le
        self.device = device or _connect(le.ColorSensor(), card)

    def read(self):
        value = self.device.sensor.reflection
        return None if value != value else float(value)  # NaN until first update

    def close(self):
        self.device.disconnect()


class ConsoleMotors:
    """Stand-in for dry runs: prints wheel speeds instead of moving."""

    def set_speeds(self, left, right):
        print(f"motors  left={left:4d}  right={right:4d}")


class SteadyLight:
    """Stand-in for dry runs: a sensor that never changes."""

    def __init__(self, level=50.0):
        self.level = level

    def read(self):
        return self.level
