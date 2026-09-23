import tkinter as tk

import pytest

import MQTT
from whistlebot.referee import Referee


class FakeLink:
    def __init__(self, on_payload, topic=MQTT.TEST_TOPIC):
        self.on_payload = on_payload
        self.topic = topic
        self.published = []
        self.connected = False
        self.stopped = False

    def publish(self, payload):
        self.published.append(payload)

    def stop(self):
        self.stopped = True


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    r.withdraw()
    yield r
    try:
        r.destroy()
    except tk.TclError:
        pass


def make(root, topic=MQTT.TEST_TOPIC):
    links = []

    def make_link(on_payload):
        links.append(FakeLink(on_payload, topic))
        return links[-1]

    ref = Referee(root, make_link, broker="b:1883", clock=lambda fmt: "12:00:00")
    return ref, links[0]


def test_buttons_publish_agreed_messages(root):
    ref, link = make(root)
    for payload in (MQTT.START, MQTT.BALL_CAUGHT, MQTT.BALL_SCORED):
        ref.send(payload)
    assert link.published == ["start", "ball_caught", "ball_scored"]
    assert "→ ball_scored" in ref.log_text()


def test_incoming_messages_are_logged(root):
    ref, link = make(root)
    link.on_payload("ball_caught")   # as if from the MQTT thread
    ref._poll()
    assert "12:00:00  ← ball_caught" in ref.log_text()


def test_custom_message(root):
    ref, link = make(root)
    ref.custom.set("  hello  ")
    ref.send_custom()
    assert link.published == ["hello"] and ref.custom.get() == ""
    ref.custom.set("   ")
    ref.send_custom()
    assert link.published == ["hello"]  # blank isn't sent


def test_status_shows_connection(root):
    ref, link = make(root)
    ref._poll()
    assert "connecting" in ref.status.cget("text")
    link.connected = True
    ref._poll()
    assert "● connected" in ref.status.cget("text")
    assert MQTT.TEST_TOPIC in ref.status.cget("text")


def label_texts(widget):
    out = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Label):
            out.append(child.cget("text"))
        out += label_texts(child)
    return out


def test_warns_on_class_topic(root):
    ref, _ = make(root, topic=MQTT.TOPIC)
    assert any("LIVE CLASS TOPIC" in t for t in label_texts(root))


def test_no_warning_on_test_topic(root):
    ref, _ = make(root)
    assert not any("LIVE CLASS TOPIC" in t for t in label_texts(root))


def test_clear_and_close(root):
    ref, link = make(root)
    ref.send("start")
    ref.clear()
    assert ref.log_text() == ""
    ref.close()
    assert link.stopped
