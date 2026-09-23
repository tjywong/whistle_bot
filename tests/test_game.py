from whistlebot.commands import Command
from whistlebot.game import Action, Game, Phase, Role
from whistlebot.protocol import Event


def started(role):
    g = Game(role)
    g.on_event(Event.START)
    return g


def test_waits_for_start():
    g = Game(Role.BALL)
    assert not g.driving
    assert g.on_event(Event.START) == [Action.ENABLE_DRIVE]
    assert g.driving


def test_nothing_happens_before_start():
    g = Game(Role.BALL)
    assert g.on_light_tripped() == []
    assert g.on_command(Command.GOAL) == []
    assert g.phase is Phase.WAITING


def test_repeated_start_while_playing_is_ignored():
    assert started(Role.BALL).on_event(Event.START) == []


def test_ball_caught():
    g = started(Role.BALL)
    assert g.on_light_tripped() == [Action.HALT, Action.PUBLISH_CAUGHT, Action.PLAY_DEFEAT]
    assert g.phase is Phase.LOST


def test_ball_scores():
    g = started(Role.BALL)
    assert g.on_command(Command.GOAL) == [Action.HALT, Action.PUBLISH_SCORED, Action.PLAY_VICTORY]
    assert g.phase is Phase.WON


def test_ball_ignores_echo_of_its_own_message():
    g = started(Role.BALL)
    g.on_light_tripped()
    assert g.on_event(Event.BALL_CAUGHT) == []
    assert g.phase is Phase.LOST


def test_only_first_outcome_counts():
    g = started(Role.BALL)
    g.on_command(Command.GOAL)
    assert g.on_light_tripped() == []
    assert g.phase is Phase.WON


def test_goalie_wins_when_ball_caught():
    g = started(Role.GOALIE)
    assert g.on_event(Event.BALL_CAUGHT) == [Action.HALT, Action.PLAY_VICTORY]
    assert g.phase is Phase.WON


def test_goalie_loses_when_ball_scores():
    g = started(Role.GOALIE)
    assert g.on_event(Event.BALL_SCORED) == [Action.HALT, Action.PLAY_DEFEAT]
    assert g.phase is Phase.LOST


def test_goalie_ignores_light_and_goal_whistle():
    g = started(Role.GOALIE)
    assert g.on_light_tripped() == []
    assert g.on_command(Command.GOAL) == []
    assert g.phase is Phase.PLAYING


def test_start_after_round_begins_new_round():
    g = started(Role.BALL)
    g.on_light_tripped()
    assert g.on_event(Event.START) == [Action.ENABLE_DRIVE]
    assert g.phase is Phase.PLAYING
