from whistlebot.sensing import LightGuard


def feed_all(guard, readings):
    return [guard.update(r) for r in readings]


def test_first_reading_is_baseline():
    g = LightGuard()
    g.update(60)
    assert g.baseline == 60


def test_trips_when_shaded():
    g = LightGuard(delta=15, trip_frames=3)
    assert feed_all(g, [60, 30, 30, 30]) == [False, False, False, True]


def test_trips_when_lit():
    g = LightGuard(delta=15, trip_frames=2)
    assert feed_all(g, [40, 90, 90]) == [False, False, True]


def test_small_changes_ignored():
    g = LightGuard(delta=15, trip_frames=2)
    assert not any(feed_all(g, [60, 55, 50, 65, 70]))


def test_flicker_must_be_consecutive():
    g = LightGuard(delta=15, trip_frames=3)
    assert not any(feed_all(g, [60, 30, 30, 60, 30, 30]))


def test_trip_reported_once():
    g = LightGuard(delta=15, trip_frames=1)
    assert feed_all(g, [60, 30, 30, 30]) == [False, True, False, False]


def test_missing_readings_are_skipped():
    g = LightGuard(delta=15, trip_frames=1)
    assert feed_all(g, [None, 60, None, 30]) == [False, False, False, True]
    assert g.baseline == 60


def test_reset_recalibrates():
    g = LightGuard(delta=15, trip_frames=1)
    feed_all(g, [60, 30])
    g.reset()
    assert feed_all(g, [30, 30, 60]) == [False, False, True]
