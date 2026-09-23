"""Convert commands into left/right wheel speeds for the double motor."""

from .commands import Command


class Drive:
    """Keeps speed, direction and steering state and pushes it to the motors.

    FORWARD/BACKWARD pick the direction of travel (starting at ``step`` if
    stopped). SPEED_UP adds ``step`` (up to ``max_speed``) in the current
    direction and straightens out. LEFT/RIGHT keep turning until the next
    command; while stopped they pivot in place so you can aim at the goal.
    STOP zeroes everything and resets the direction to forward.
    """

    def __init__(self, motors, step=20, max_speed=100, turn_ratio=0.4):
        self.motors = motors
        self.step = step
        self.max_speed = max_speed
        self.turn_ratio = turn_ratio
        self.speed = 0       # magnitude, 0..max_speed
        self.direction = 1   # +1 forward, -1 backward
        self.steer = 0       # -1 left, 0 straight, +1 right

    def apply(self, cmd):
        if cmd is Command.SPEED_UP:
            self.speed = min(self.speed + self.step, self.max_speed)
            self.steer = 0
        elif cmd in (Command.FORWARD, Command.BACKWARD):
            self.direction = 1 if cmd is Command.FORWARD else -1
            self.speed = self.speed or self.step
            self.steer = 0
        elif cmd is Command.STOP:
            self.speed = 0
            self.direction = 1
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
            v = self.speed * self.direction
            return v, v
        if self.speed == 0:
            pivot = self.step * self.steer
            return pivot, -pivot
        fast = self.speed * self.direction
        slow = round(self.speed * self.turn_ratio) * self.direction
        if self.steer < 0:
            return slow, fast
        return fast, slow

    def halt(self):
        self.speed = 0
        self.direction = 1
        self.steer = 0
        self.motors.set_speeds(0, 0)
