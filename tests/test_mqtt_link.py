import argparse
from types import SimpleNamespace

import pytest

from MQTT import TEST_TOPIC, add_topic_args

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

    def publish(self, topic, payload, qos=0):
        self.published.append((topic, payload, qos))


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
    assert client.published == [(TOPIC, "ball_scored", 1)]


def test_stop():
    link, client, _ = make()
    link.start()
    link.stop()
    assert client.connected is None and not client.looping


def test_custom_topic():
    received = []
    client = FakeClient()
    link = MqttLink("b", received.append, topic=TEST_TOPIC, client=client)
    client.on_connect(client, None, {}, 0, None)
    link.publish("start")
    assert client.subscribed == [TEST_TOPIC]
    assert client.published == [(TEST_TOPIC, "start", 1)]


def test_connected_flag_tracks_connection():
    link, client, _ = make()
    assert not link.connected
    client.on_connect(client, None, {}, 0, None)
    assert link.connected
    client.on_disconnect(client, None, {}, 0, None)
    assert not link.connected


def parse(argv):
    parser = argparse.ArgumentParser()
    add_topic_args(parser)
    return parser.parse_args(argv)


def test_topic_args():
    assert parse([]).topic == TOPIC
    assert parse(["--test-topic"]).topic == TEST_TOPIC == "ME193/Rogers/tyler-test"
    assert parse(["--topic", "x/y"]).topic == "x/y"


def test_topic_args_are_exclusive():
    with pytest.raises(SystemExit):
        parse(["--test-topic", "--topic", "x"])
