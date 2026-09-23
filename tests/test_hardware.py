from types import SimpleNamespace

import legoeducation as le
import pytest

from whistlebot.hardware import LegoDoubleMotor, LegoLightSensor, _connect, parse_card

CW = le.MOTOR_MOVE_DIRECTION_CLOCKWISE
CCW = le.MOTOR_MOVE_DIRECTION_COUNTERCLOCKWISE


class FakeLegoDevice:
    search_name = "Double Motor"

    def __init__(self, connects=True):
        self.calls = []
        self.connects = connects
        self.connected = False

    def connect(self, **kw):
        self.calls.append(("connect", kw))
        self.connected = self.connects

    def disconnect(self):
        self.calls.append(("disconnect",))

    def motor_run(self, **kw):
        self.calls.append(("run", kw["motor"], kw["direction"], kw["speed"]))

    def motor_stop(self, **kw):
        self.calls.append(("stop", kw["motor"]))


def motor():
    dev = FakeLegoDevice()
    return LegoDoubleMotor(device=dev), dev


def test_parse_card():
    assert parse_card("Blue:3685") == ("blue", "3685")
    assert parse_card("red:0049") == ("red", "0049")  # keeps leading zeros
    with pytest.raises(ValueError):
        parse_card("3685")


def test_connect_uses_card_filter():
    dev = FakeLegoDevice()
    _connect(dev, ("blue", "3685"))
    assert dev.calls == [("connect", {"card_color": le.LEGO_COLOR_BLUE, "card_serial": "3685"})]


def test_connect_failure_raises():
    with pytest.raises(RuntimeError, match="blue 3685"):
        _connect(FakeLegoDevice(connects=False), ("blue", "3685"))


def test_unknown_card_color():
    with pytest.raises(ValueError):
        _connect(FakeLegoDevice(), ("plaid", "1"))


def test_forward_spins_sides_opposite_ways():
    m, dev = motor()
    m.set_speeds(40, 40)
    assert dev.calls == [("run", le.MOTOR_LEFT, CCW, 40), ("run", le.MOTOR_RIGHT, CW, 40)]


def test_reverse_flips_directions():
    m, dev = motor()
    m.set_speeds(-20, -20)
    assert dev.calls == [("run", le.MOTOR_LEFT, CW, 20), ("run", le.MOTOR_RIGHT, CCW, 20)]


def test_pivot_left():
    m, dev = motor()
    m.set_speeds(-20, 20)
    assert dev.calls == [("run", le.MOTOR_LEFT, CW, 20), ("run", le.MOTOR_RIGHT, CW, 20)]


def test_full_stop_stops_both():
    m, dev = motor()
    m.set_speeds(0, 0)
    assert dev.calls == [("stop", le.MOTOR_BOTH)]


def test_one_side_zero_stops_that_side():
    m, dev = motor()
    m.set_speeds(0, 30)
    assert dev.calls == [("stop", le.MOTOR_LEFT), ("run", le.MOTOR_RIGHT, CW, 30)]


def test_reversed_flags_are_configurable():
    dev = FakeLegoDevice()
    m = LegoDoubleMotor(left_reversed=False, right_reversed=True, device=dev)
    m.set_speeds(10, 10)
    assert dev.calls == [("run", le.MOTOR_LEFT, CW, 10), ("run", le.MOTOR_RIGHT, CCW, 10)]


def test_speed_clamped():
    m, dev = motor()
    m.set_speeds(150, 150)
    assert all(c[3] == 100 for c in dev.calls)


def test_close_stops_then_disconnects():
    m, dev = motor()
    m.close()
    assert dev.calls == [("stop", le.MOTOR_BOTH), ("disconnect",)]


def test_light_sensor_reads_reflection():
    dev = SimpleNamespace(sensor=SimpleNamespace(reflection=42))
    assert LegoLightSensor(None, device=dev).read() == 42.0


def test_light_sensor_none_before_first_reading():
    dev = SimpleNamespace(sensor=SimpleNamespace(reflection=float("nan")))
    assert LegoLightSensor(None, device=dev).read() is None
