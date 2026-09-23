from whistlebot.commands import Command
from whistlebot.drive import Drive
from tests.helpers import FakeMotors


def make(**kw):
    motors = FakeMotors()
    return Drive(motors, **kw), motors


def test_forward_is_full_speed():
    drive, motors = make(step=20, max_speed=100)
    drive.apply(Command.FORWARD)
    assert motors.last == (100, 100)


def test_backward_is_full_speed_reverse():
    drive, motors = make(step=20, max_speed=100)
    drive.apply(Command.BACKWARD)
    assert motors.last == (-100, -100)


def test_forward_and_backward_reset_to_full_speed():
    drive, motors = make(step=20)
    drive.apply(Command.FORWARD)
    drive.apply(Command.SLOW_DOWN)
    drive.apply(Command.BACKWARD)
    assert motors.last == (-100, -100)
    drive.apply(Command.SLOW_DOWN)
    drive.apply(Command.FORWARD)
    assert motors.last == (100, 100)


def test_slow_down_steps_down_to_a_floor():
    drive, motors = make(step=20, max_speed=100)
    drive.apply(Command.FORWARD)
    speeds = []
    for _ in range(6):
        drive.apply(Command.SLOW_DOWN)
        speeds.append(motors.last[0])
    assert speeds == [80, 60, 40, 20, 20, 20]   # never stops on its own


def test_slow_down_while_reversing():
    drive, motors = make(step=20)
    drive.apply(Command.BACKWARD)
    drive.apply(Command.SLOW_DOWN)
    assert motors.last == (-80, -80)


def test_slow_down_when_stopped_stays_stopped():
    drive, motors = make()
    drive.apply(Command.SLOW_DOWN)
    assert drive.speed == 0 and motors.last == (0, 0)


def test_slow_down_straightens():
    drive, motors = make(step=20)
    drive.apply(Command.FORWARD)
    drive.apply(Command.LEFT)
    drive.apply(Command.SLOW_DOWN)
    assert motors.last == (80, 80)


def test_stop_zeroes():
    drive, motors = make()
    drive.apply(Command.FORWARD)
    drive.apply(Command.STOP)
    assert motors.last == (0, 0)


def test_turn_left_slows_left_wheel():
    drive, motors = make(turn_ratio=0.4)
    drive.apply(Command.FORWARD)
    drive.apply(Command.LEFT)
    assert motors.last == (40, 100)


def test_turn_right_slows_right_wheel():
    drive, motors = make(turn_ratio=0.4)
    drive.apply(Command.FORWARD)
    drive.apply(Command.RIGHT)
    assert motors.last == (100, 40)


def test_turning_while_reversing():
    drive, motors = make(turn_ratio=0.4)
    drive.apply(Command.BACKWARD)
    drive.apply(Command.LEFT)
    assert motors.last == (-40, -100)
    drive.apply(Command.RIGHT)
    assert motors.last == (-100, -40)


def test_turn_while_stopped_pivots():
    drive, motors = make(step=20)
    drive.apply(Command.LEFT)
    assert motors.last == (-20, 20)
    drive.apply(Command.RIGHT)
    assert motors.last == (20, -20)


def test_forward_straightens():
    drive, motors = make()
    drive.apply(Command.FORWARD)
    drive.apply(Command.LEFT)
    drive.apply(Command.FORWARD)
    assert motors.last == (100, 100)


def test_stop_resets_direction():
    drive, motors = make()
    drive.apply(Command.BACKWARD)
    drive.apply(Command.STOP)
    drive.apply(Command.LEFT)   # pivot direction is independent of old direction
    assert motors.last == (-20, 20)


def test_goal_command_does_not_touch_motors():
    drive, motors = make()
    drive.apply(Command.GOAL)
    assert motors.calls == []


def test_halt():
    drive, motors = make()
    drive.apply(Command.FORWARD)
    drive.apply(Command.RIGHT)
    drive.halt()
    assert (drive.speed, drive.steer, motors.last) == (0, 0, (0, 0))
