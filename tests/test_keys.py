import tkinter as tk
from types import SimpleNamespace

import pytest

from whistlebot.keys import bind_quit


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    r.withdraw()
    yield r
    r.destroy()


def test_q_calls_callback(root):
    calls = []
    handler = bind_quit(root, lambda: calls.append(1))
    assert handler(SimpleNamespace(widget=root)) == "break"
    assert calls == [1]


def test_q_ignored_while_typing(root):
    calls = []
    handler = bind_quit(root, lambda: calls.append(1))
    handler(SimpleNamespace(widget=tk.Entry(root)))
    assert calls == []


def test_binding_registered_for_both_cases(root):
    bind_quit(root, lambda: None)
    assert root.bind_all("<KeyPress-q>") and root.bind_all("<KeyPress-Q>")
