from whistlebot.commands import Command
from whistlebot.drive import Drive
from tests.helpers import FakeMotors


def make(**kw):
    motors = FakeMotors()
    return Drive(motors, **kw), motors


def test_speed_up_increments_and_caps():
    drive, motors = make(step=40, max_speed=100)
    for _ in range(4):
        drive.apply(Command.SPEED_UP)
    assert drive.speed == 100
    assert motors.last == (100, 100)


def test_stop_zeroes():
    drive, motors = make()
    drive.apply(Command.SPEED_UP)
    drive.apply(Command.STOP)
    assert motors.last == (0, 0)


def test_turn_left_slows_left_wheel():
    drive, motors = make(step=50, turn_ratio=0.4)
    drive.apply(Command.SPEED_UP)
    drive.apply(Command.LEFT)
    assert motors.last == (20, 50)


def test_turn_right_slows_right_wheel():
    drive, motors = make(step=50, turn_ratio=0.4)
    drive.apply(Command.SPEED_UP)
    drive.apply(Command.RIGHT)
    assert motors.last == (50, 20)


def test_speed_up_straightens():
    drive, motors = make(step=20)
    drive.apply(Command.SPEED_UP)
    drive.apply(Command.LEFT)
    drive.apply(Command.SPEED_UP)
    assert motors.last == (40, 40)


def test_turn_while_stopped_pivots():
    drive, motors = make(step=20)
    drive.apply(Command.LEFT)
    assert motors.last == (-20, 20)
    drive.apply(Command.RIGHT)
    assert motors.last == (20, -20)


def test_forward_from_stop_starts_slow():
    drive, motors = make(step=20)
    drive.apply(Command.FORWARD)
    assert motors.last == (20, 20)


def test_backward_from_stop_reverses():
    drive, motors = make(step=20)
    drive.apply(Command.BACKWARD)
    assert motors.last == (-20, -20)


def test_backward_keeps_current_speed():
    drive, motors = make(step=20)
    drive.apply(Command.SPEED_UP)
    drive.apply(Command.SPEED_UP)
    drive.apply(Command.BACKWARD)
    assert motors.last == (-40, -40)
    drive.apply(Command.FORWARD)
    assert motors.last == (40, 40)


def test_speed_up_while_reversing_goes_faster_backwards():
    drive, motors = make(step=20)
    drive.apply(Command.BACKWARD)
    drive.apply(Command.SPEED_UP)
    assert motors.last == (-40, -40)


def test_turning_while_reversing():
    drive, motors = make(step=50, turn_ratio=0.4)
    drive.apply(Command.BACKWARD)
    drive.apply(Command.LEFT)
    assert motors.last == (-20, -50)
    drive.apply(Command.RIGHT)
    assert motors.last == (-50, -20)


def test_forward_straightens():
    drive, motors = make(step=20)
    drive.apply(Command.FORWARD)
    drive.apply(Command.LEFT)
    drive.apply(Command.FORWARD)
    assert motors.last == (20, 20)


def test_stop_resets_direction():
    drive, motors = make(step=20)
    drive.apply(Command.BACKWARD)
    drive.apply(Command.STOP)
    drive.apply(Command.SPEED_UP)
    assert motors.last == (20, 20)


def test_goal_command_does_not_touch_motors():
    drive, motors = make()
    drive.apply(Command.GOAL)
    assert motors.calls == []


def test_halt():
    drive, motors = make()
    drive.apply(Command.SPEED_UP)
    drive.apply(Command.RIGHT)
    drive.halt()
    assert (drive.speed, drive.steer, motors.last) == (0, 0, (0, 0))
