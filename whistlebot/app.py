"""Glue: one step per audio chunk ties pitch, game rules, drive and I/O together."""

import queue

from .commands import Command
from .game import Action, Game
from .pitch import dominant_frequency, rms
from .protocol import Event, Messages
from .songs import DEFEAT, VICTORY, synthesize


class BotApp:
    def __init__(self, role, drive, light, guard, decoder, publish, play,
                 messages=Messages(), detector=dominant_frequency, log=print):
        self.game = Game(role)
        self.drive = drive
        self.light = light
        self.guard = guard
        self.decoder = decoder
        self.publish = publish
        self.play = play
        self.messages = messages
        self.detector = detector
        self.log = log
        self.last_message = None    # "what we heard -> what we did", for the HUD
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
            self._handle_payload(payload)

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

    def _handle_payload(self, payload):
        event = self.messages.decode(payload)
        phase = self.game.phase.value
        if event is None:
            outcome = "not a game message, ignored"
        else:
            actions = self.game.on_event(event)
            if actions:
                outcome = ", ".join(a.value for a in actions)
            elif self.game.phase.value == "waiting":
                outcome = "ignored: round not started (send 'start' first)"
            else:
                outcome = f"ignored while {phase}"
            self._run(actions)
        self.last_message = f"'{payload}' -> {outcome}"
        self.log(f"MQTT {self.last_message}")

    def _run(self, actions):
        for action in actions:
            if action is Action.ENABLE_DRIVE:
                self.guard.reset()
                self.drive.halt()
                self.log("Round started: whistle to drive")
            elif action is Action.HALT:
                self.drive.halt()
            elif action in (Action.PUBLISH_CAUGHT, Action.PUBLISH_SCORED):
                event = Event.BALL_CAUGHT if action is Action.PUBLISH_CAUGHT else Event.BALL_SCORED
                payload = self.messages.encode(event)
                self.log(f"MQTT sending '{payload}'")
                self.publish(payload)
            elif action is Action.PLAY_VICTORY:
                self.log("Playing victory song")
                self.play(synthesize(VICTORY))
            elif action is Action.PLAY_DEFEAT:
                self.log("Playing defeat song")
                self.play(synthesize(DEFEAT))
