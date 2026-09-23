#!/usr/bin/env python3
"""MQTT for the ME193 World Cup: the topic, the agreed messages, and the client.

whistle_bot.py drives the car (whistle -> motors, light sensor, songs) and
talks to the other robot through this module, via whistlebot.protocol and
whistlebot.mqtt_link. Agree on the three messages below with your
opponent before the match; this is the only place to change them.

Game-day helper (no robot needed):

    python MQTT.py --broker <host> start            # kick off the round
    python MQTT.py --broker <host> send ball_scored # publish any message
    python MQTT.py --broker <host> watch            # print everything on the topic
    python MQTT.py --broker <host> referee          # window with buttons + live log

Add --test-topic to any of these (and to whistle_bot.py) to use a private
topic for solo testing, so classmates' robots on the class topic are
not started or stopped by your tests.
"""

import argparse
import time

import paho.mqtt.client as mqtt

TOPIC = "ME193/Rogers"
TEST_TOPIC = "ME193/Rogers/tyler-test"  # solo testing; class robots don't hear it

# Messages shared with the opponent (matched case-insensitively).
START = "start"              # referee -> both: round begins, whistle driving enabled
BALL_CAUGHT = "ball_caught"  # ball -> goalie: goalie reached my light sensor, I failed
BALL_SCORED = "ball_scored"  # ball -> goalie: I made it into the goal


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
        self.connected = False
        self.client = client or mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def start(self):
        self.client.connect(self.broker, self.port)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, payload):
        # QoS 1 so a message sent while (re)connecting is delivered, not dropped.
        return self.client.publish(self.topic, payload, qos=1)

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        # Subscribing here means we re-subscribe after any reconnect.
        self.connected = True
        client.subscribe(self.topic)

    def _on_disconnect(self, client, userdata, *args):
        self.connected = False

    def _on_message(self, client, userdata, msg):
        self.on_payload(msg.payload.decode("utf-8", errors="replace"))


def add_topic_args(parser):
    """--topic / --test-topic, both stored in ``args.topic``."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--topic", default=TOPIC,
                       help=f"MQTT topic (default: the class topic {TOPIC})")
    group.add_argument("--test-topic", dest="topic", action="store_const", const=TEST_TOPIC,
                       help=f"use the private test topic {TEST_TOPIC}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--broker", required=True, help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883)
    add_topic_args(parser)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("start", help=f"publish {START!r}")
    send = sub.add_parser("send", help="publish a message")
    send.add_argument("message")
    sub.add_parser("watch", help="print every message on the topic")
    sub.add_parser("referee", help="window with Start / Ball caught / Ball scored buttons")
    args = parser.parse_args()

    if args.cmd == "referee":
        from whistlebot.referee import run
        run(args.broker, args.port, args.topic)
        return

    link = MqttLink(args.broker, lambda p: print(f"{args.topic}: {p}"),
                    port=args.port, topic=args.topic)
    link.start()
    try:
        if args.cmd == "watch":
            print(f"watching {args.topic} on {args.broker} (Ctrl+C to stop)")
            while True:
                time.sleep(1)
        payload = START if args.cmd == "start" else args.message
        link.publish(payload).wait_for_publish(timeout=5)
        print(f"published {payload!r} to {args.topic}")
    except KeyboardInterrupt:
        pass
    finally:
        link.stop()


if __name__ == "__main__":
    main()
