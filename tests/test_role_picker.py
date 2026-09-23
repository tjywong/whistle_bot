import tkinter as tk

import pytest

from whistlebot.game import Role
from whistlebot.role_picker import RolePicker, validate_choice


def test_goalie_needs_no_card():
    assert validate_choice("goalie", "") == (Role.GOALIE, None)


def test_ball_with_card():
    assert validate_choice(Role.BALL, " red:1234 ") == (Role.BALL, ("red", "1234"))


def test_blank_card_uses_motor_card():
    assert validate_choice("ball", "", default_card=("blue", "3685")) == (Role.BALL, ("blue", "3685"))


def test_typed_card_overrides_motor_card():
    assert validate_choice("ball", "red:1", default_card=("blue", "3685")) == (Role.BALL, ("red", "1"))


def test_ball_without_card_rejected():
    with pytest.raises(ValueError, match="Color Sensor"):
        validate_choice("ball", "")


def test_ball_without_card_ok_in_dry_run():
    assert validate_choice("ball", "", need_sensor=False) == (Role.BALL, None)


def test_bad_card_rejected():
    with pytest.raises(ValueError):
        validate_choice("ball", "1234")


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    r.withdraw()
    yield r
    r.destroy()


def test_picker_connects_sensor_for_ball(root):
    connected = []
    picker = RolePicker(root, "ok", ("red", "1"), connect_sensor=connected.append)
    picker._pick(Role.BALL)
    assert picker.result == (Role.BALL, ("red", "1")) and connected == [("red", "1")]


def test_picker_shows_connect_error_and_stays_open(root):
    def fail(card):
        raise RuntimeError("could not connect")

    picker = RolePicker(root, "ok", ("red", "1"), connect_sensor=fail)
    picker._pick(Role.BALL)
    assert picker.result is None
    assert "could not connect" in picker.error.cget("text")
    assert picker.win.winfo_exists()


def test_picker_goalie_skips_sensor(root):
    connected = []
    picker = RolePicker(root, "ok", connect_sensor=connected.append)
    picker._pick(Role.GOALIE)
    assert picker.result == (Role.GOALIE, None) and connected == []


def test_picker_prefills_and_connects_with_motor_card(root):
    connected = []
    picker = RolePicker(root, "ok", connect_sensor=connected.append, motor_card=("blue", "3685"))
    assert picker.card.get() == "blue:3685"
    picker._pick(Role.BALL)
    assert connected == [("blue", "3685")] and picker.result == (Role.BALL, ("blue", "3685"))


def test_picker_blank_card_falls_back_to_motor_card(root):
    connected = []
    picker = RolePicker(root, "ok", connect_sensor=connected.append, motor_card=("blue", "3685"))
    picker.card.set("")
    picker._pick(Role.BALL)
    assert connected == [("blue", "3685")]


def test_sensor_card_option_beats_motor_card(root):
    picker = RolePicker(root, "ok", ("red", "7"), motor_card=("blue", "3685"))
    assert picker.card.get() == "red:7"
