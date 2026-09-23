"""MQTT messages shared with the opponent. The agreed text lives in MQTT.py."""

from dataclasses import dataclass
from enum import Enum

import MQTT
from MQTT import TOPIC


class Event(Enum):
    START = "start"
    BALL_CAUGHT = "ball_caught"  # ball -> goalie: goalie reached the sensor
    BALL_SCORED = "ball_scored"  # ball -> goalie: ball made it into the goal


@dataclass(frozen=True)
class Messages:
    """Payload text for each event. Defaults come from MQTT.py."""
    start: str = MQTT.START
    ball_caught: str = MQTT.BALL_CAUGHT
    ball_scored: str = MQTT.BALL_SCORED

    def encode(self, event):
        return {
            Event.START: self.start,
            Event.BALL_CAUGHT: self.ball_caught,
            Event.BALL_SCORED: self.ball_scored,
        }[event]

    def decode(self, payload):
        """Return the Event for a payload, or None if it isn't one of ours."""
        text = payload.strip().lower()
        for event in Event:
            if text == self.encode(event).lower():
                return event
        return None
