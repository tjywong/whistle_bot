"""Keyboard shortcut for quitting from any window of the app."""

import tkinter as tk


def bind_quit(root, callback, key="q"):
    """Call ``callback`` when ``key`` is pressed in any of the app's windows.

    Ignored while typing in a text field so entering values can't quit.
    Returns the handler (handy for tests).
    """
    def handler(event):
        if isinstance(event.widget, tk.Entry):
            return None
        callback()
        return "break"

    root.bind_all(f"<KeyPress-{key.lower()}>", handler)
    root.bind_all(f"<KeyPress-{key.upper()}>", handler)
    return handler
