"""Thin wrapper around paho-mqtt for one topic."""

import paho.mqtt.client as mqtt

from .protocol import TOPIC


class MqttLink:
    """Subscribes to ``topic`` and hands each payload (as str) to ``on_payload``.

    ``on_payload`` runs on paho's network thread, so keep it quick
    (e.g. ``queue.put``). Pass ``client`` to inject a fake in tests.
    """

    def __init__(self, broker, on_payload, port=1883, topic=TOPIC, client=None):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.on_payload = on_payload
        self.client = client or mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def start(self):
        self.client.connect(self.broker, self.port)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, payload):
        self.client.publish(self.topic, payload)

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        # Subscribing here means we re-subscribe after any reconnect.
        client.subscribe(self.topic)

    def _on_message(self, client, userdata, msg):
        self.on_payload(msg.payload.decode("utf-8", errors="replace"))
