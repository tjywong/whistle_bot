"""Match rules for the ball and goalie roles, with no hardware attached."""

from enum import Enum

from .commands import Command
from .protocol import Event


class Role(Enum):
    BALL = "ball"
    GOALIE = "goalie"


class Phase(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


class Action(Enum):
    ENABLE_DRIVE = "enable_drive"
    HALT = "halt"
    PUBLISH_CAUGHT = "publish_caught"
    PUBLISH_SCORED = "publish_scored"
    PLAY_VICTORY = "play_victory"
    PLAY_DEFEAT = "play_defeat"


class Game:
    """State machine: each handler returns the actions the robot must take.

    Only the ball publishes results. Once a round ends, further events
    (including the echo of our own MQTT message) are ignored until the
    next "start".
    """

    def __init__(self, role):
        self.role = role
        self.phase = Phase.WAITING

    @property
    def driving(self):
        return self.phase is Phase.PLAYING

    def on_event(self, event):
        if event is Event.START:
            if self.phase is Phase.PLAYING:
                return []
            self.phase = Phase.PLAYING
            return [Action.ENABLE_DRIVE]

        if self.role is Role.GOALIE and self.phase is Phase.PLAYING:
            if event is Event.BALL_CAUGHT:
                return self._finish(won=True)
            if event is Event.BALL_SCORED:
                return self._finish(won=False)
        return []

    def on_light_tripped(self):
        if self.role is Role.BALL and self.phase is Phase.PLAYING:
            return self._finish(won=False, publish=Action.PUBLISH_CAUGHT)
        return []

    def on_command(self, cmd):
        if cmd is Command.GOAL and self.role is Role.BALL and self.phase is Phase.PLAYING:
            return self._finish(won=True, publish=Action.PUBLISH_SCORED)
        return []

    def _finish(self, won, publish=None):
        self.phase = Phase.WON if won else Phase.LOST
        actions = [Action.HALT]
        if publish:
            actions.append(publish)
        actions.append(Action.PLAY_VICTORY if won else Action.PLAY_DEFEAT)
        return actions
