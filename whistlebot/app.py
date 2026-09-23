"""Glue: one step per audio chunk ties pitch, game rules, drive and I/O together."""

import queue

from .commands import Command
from .game import Action, Game
from .pitch import dominant_frequency, rms
from .protocol import Event, Messages
from .songs import DEFEAT, VICTORY, synthesize


class BotApp:
    def __init__(self, role, drive, light, guard, decoder, publish, play,
                 messages=Messages(), detector=dominant_frequency):
        self.game = Game(role)
        self.drive = drive
        self.light = light
        self.guard = guard
        self.decoder = decoder
        self.publish = publish
        self.play = play
        self.messages = messages
        self.detector = detector
        self.inbox = queue.Queue()  # filled from the MQTT thread
        self.last_freq = None       # read by the HUD
        self.last_command = None
        self.last_rms = 0.0

    def step(self, samples):
        """Process pending MQTT messages, the light sensor, then one audio chunk."""
        while True:
            try:
                payload = self.inbox.get_nowait()
            except queue.Empty:
                break
            event = self.messages.decode(payload)
            if event is not None:
                self._run(self.game.on_event(event))

        if self.game.driving and self.guard.update(self.light.read()):
            self._run(self.game.on_light_tripped())

        self.last_rms = rms(samples)
        self.last_freq = self.detector(samples)
        cmd = self.decoder.feed(self.last_freq)
        if cmd is None:
            return
        self.last_command = cmd
        if cmd is Command.GOAL:
            self._run(self.game.on_command(cmd))
        elif self.game.driving:
            self.drive.apply(cmd)

    def _run(self, actions):
        for action in actions:
            if action is Action.ENABLE_DRIVE:
                self.guard.reset()
                self.drive.halt()
            elif action is Action.HALT:
                self.drive.halt()
            elif action is Action.PUBLISH_CAUGHT:
                self.publish(self.messages.encode(Event.BALL_CAUGHT))
            elif action is Action.PUBLISH_SCORED:
                self.publish(self.messages.encode(Event.BALL_SCORED))
            elif action is Action.PLAY_VICTORY:
                self.play(synthesize(VICTORY))
            elif action is Action.PLAY_DEFEAT:
                self.play(synthesize(DEFEAT))
