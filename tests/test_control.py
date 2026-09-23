import threading

from whistlebot.control import ControlLoop


class CountingApp:
    def __init__(self, stop_after, loop_ref):
        self.steps = []
        self.stop_after = stop_after
        self.loop_ref = loop_ref
        self.done = threading.Event()

    def step(self, samples):
        self.steps.append(samples)
        if len(self.steps) >= self.stop_after:
            self.done.set()


def test_feeds_chunks_until_stopped():
    chunks = iter(range(1000))
    app = CountingApp(5, None)
    loop = ControlLoop(app, lambda: next(chunks))
    loop.start()
    assert app.done.wait(2)
    loop.stop()
    assert not loop.is_alive()
    assert app.steps[:5] == [0, 1, 2, 3, 4]
    assert loop.latest_samples == app.steps[-1]


def test_error_is_captured():
    def boom():
        raise OSError("mic unplugged")

    loop = ControlLoop(CountingApp(1, None), boom)
    loop.start()
    loop.join(2)
    assert isinstance(loop.error, OSError)
