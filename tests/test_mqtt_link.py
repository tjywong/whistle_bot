from types import SimpleNamespace

from whistlebot.mqtt_link import MqttLink
from whistlebot.protocol import TOPIC


class FakeClient:
    def __init__(self):
        self.subscribed, self.published, self.connected = [], [], None
        self.looping = False

    def connect(self, host, port):
        self.connected = (host, port)

    def loop_start(self):
        self.looping = True

    def loop_stop(self):
        self.looping = False

    def disconnect(self):
        self.connected = None

    def subscribe(self, topic):
        self.subscribed.append(topic)

    def publish(self, topic, payload):
        self.published.append((topic, payload))


def make():
    received = []
    client = FakeClient()
    link = MqttLink("broker.local", received.append, client=client)
    return link, client, received


def test_start_connects_and_loops():
    link, client, _ = make()
    link.start()
    assert client.connected == ("broker.local", 1883) and client.looping


def test_subscribes_on_connect():
    link, client, _ = make()
    client.on_connect(client, None, {}, 0, None)
    assert client.subscribed == [TOPIC]


def test_incoming_payload_decoded():
    link, client, received = make()
    client.on_message(client, None, SimpleNamespace(payload=b"start"))
    assert received == ["start"]


def test_publish_goes_to_topic():
    link, client, _ = make()
    link.publish("ball_scored")
    assert client.published == [(TOPIC, "ball_scored")]


def test_stop():
    link, client, _ = make()
    link.start()
    link.stop()
    assert client.connected is None and not client.looping
