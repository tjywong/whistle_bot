import pytest

from whistlebot.protocol import TOPIC, Event, Messages


def test_topic():
    assert TOPIC == "ME193/Rogers"


@pytest.mark.parametrize("event", list(Event))
def test_round_trip(event):
    m = Messages()
    assert m.decode(m.encode(event)) is event


def test_decode_is_forgiving_about_case_and_whitespace():
    assert Messages().decode("  START\n") is Event.START


def test_unknown_payload():
    assert Messages().decode("hello") is None


def test_custom_messages():
    m = Messages(ball_caught="goalie_wins")
    assert m.decode("goalie_wins") is Event.BALL_CAUGHT
    assert m.decode("ball_caught") is None
