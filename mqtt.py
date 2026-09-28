import time

import paho.mqtt.client as mqtt

BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC = "ME193"


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected ({reason_code}). Listening on '{TOPIC}'.")
    print("Type a message and press Enter to publish. Ctrl+C or Ctrl+D to quit.")
    client.subscribe(TOPIC)  # here, so it re-subscribes automatically on reconnect


def on_message(client, userdata, msg):
    print(f"\r[{msg.topic}] {msg.payload.decode()}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_start()  # network loop runs in the background so we can read input

while not client.is_connected():  # don't read input until we can actually publish
    time.sleep(0.1)

try:
    while True:
        text = input()
        if text:
            client.publish(TOPIC, text)
except (KeyboardInterrupt, EOFError):
    print("\nDisconnecting.")
finally:
    client.loop_stop()
    client.disconnect()
