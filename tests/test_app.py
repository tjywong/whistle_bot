"""End-to-end game flow with fake motors, light, MQTT and speaker."""

from whistlebot.app import BotApp
from whistlebot.commands import WhistleDecoder
from whistlebot.drive import Drive
from whistlebot.game import Phase, Role
from whistlebot.sensing import LightGuard
from whistlebot.songs import DEFEAT, VICTORY, synthesize
from tests.helpers import FakeLight, FakeMotors, silence, tone


def make(role):
    motors, light = FakeMotors(), FakeLight(50)
    published, played = [], []
    app = BotApp(role, Drive(motors, step=20), light,
                 LightGuard(delta=15, trip_frames=2),
                 WhistleDecoder(hold_frames=2, goal_hold_frames=4),
                 published.append, played.append)
    return app, motors, light, published, played


def whistle(app, freq, frames):
    for _ in range(frames):
        app.step(tone(freq))
    app.step(silence())


def start(app):
    app.inbox.put("start")
    app.step(silence())


def test_whistles_ignored_before_start():
    app, motors, *_ = make(Role.BALL)
    whistle(app, 2500, 3)
    assert motors.calls == []


def test_whistle_drives_after_start():
    app, motors, *_ = make(Role.BALL)
    start(app)
    whistle(app, 2500, 3)
    assert motors.last == (20, 20)
    whistle(app, 1200, 3)
    assert motors.last == (8, 20)
    whistle(app, 700, 3)
    assert motors.last == (0, 0)


def test_ball_caught_by_goalie():
    app, motors, light, published, played = make(Role.BALL)
    start(app)
    whistle(app, 2500, 3)
    light.level = 10
    app.step(silence())
    app.step(silence())
    assert motors.last == (0, 0)
    assert published == ["ball_caught"]
    assert played == [synthesize(DEFEAT)]
    assert app.game.phase is Phase.LOST


def test_ball_scores_with_goal_whistle():
    app, motors, light, published, played = make(Role.BALL)
    start(app)
    whistle(app, 3500, 4)
    assert published == ["ball_scored"]
    assert played == [synthesize(VICTORY)]


def test_goalie_celebrates_catch():
    app, _, _, published, played = make(Role.GOALIE)
    start(app)
    app.inbox.put("ball_caught")
    app.step(silence())
    assert played == [synthesize(VICTORY)] and published == []


def test_goalie_mourns_goal():
    app, _, _, _, played = make(Role.GOALIE)
    start(app)
    app.inbox.put("ball_scored")
    app.step(silence())
    assert played == [synthesize(DEFEAT)]


def test_no_driving_after_game_over():
    app, motors, light, *_ = make(Role.BALL)
    start(app)
    whistle(app, 3500, 4)
    n = len(motors.calls)
    whistle(app, 2500, 3)
    assert len(motors.calls) == n


def test_light_baseline_taken_at_start():
    app, _, light, published, _ = make(Role.BALL)
    light.level = 10  # darker arena than default
    start(app)
    for _ in range(5):
        app.step(silence())
    assert published == []
