"""Convert commands into left/right wheel speeds for the double motor."""

from .commands import Command


class Drive:
    """Keeps speed and steering state and pushes it to the motors.

    SPEED_UP adds ``step`` (up to ``max_speed``) and straightens out.
    LEFT/RIGHT keep turning until the next command; while stopped they
    pivot in place so you can aim at the goal. STOP zeroes everything.
    """

    def __init__(self, motors, step=20, max_speed=100, turn_ratio=0.4):
        self.motors = motors
        self.step = step
        self.max_speed = max_speed
        self.turn_ratio = turn_ratio
        self.speed = 0
        self.steer = 0  # -1 left, 0 straight, +1 right

    def apply(self, cmd):
        if cmd is Command.SPEED_UP:
            self.speed = min(self.speed + self.step, self.max_speed)
            self.steer = 0
        elif cmd is Command.STOP:
            self.speed = 0
            self.steer = 0
        elif cmd is Command.LEFT:
            self.steer = -1
        elif cmd is Command.RIGHT:
            self.steer = 1
        else:
            return
        self.motors.set_speeds(*self.outputs())

    def outputs(self):
        """Return (left, right) wheel speeds for the current state."""
        if self.steer == 0:
            return self.speed, self.speed
        if self.speed == 0:
            pivot = self.step * self.steer
            return pivot, -pivot
        slow = round(self.speed * self.turn_ratio)
        if self.steer < 0:
            return slow, self.speed
        return self.speed, slow

    def halt(self):
        self.speed = 0
        self.steer = 0
        self.motors.set_speeds(0, 0)
