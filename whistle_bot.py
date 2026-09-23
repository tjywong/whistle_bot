#!/usr/bin/env python3
"""whistle_bot: listen for a whistle and do something about it.

Startup order: connect to the Double Motor, pick ball/goalie (or calibrate
the whistle) in a popup, then start MQTT, the control loop and the HUD
window. Press q in any window to quit.
"""

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from MQTT import add_topic_args
from whistlebot import calibration as cal
from whistlebot.app import BotApp
from whistlebot.audio_io import Microphone, Speaker
from whistlebot.calibration_ui import CalibrationWindow
from whistlebot.commands import WhistleDecoder
from whistlebot.control import ControlLoop
from whistlebot.drive import Drive
from whistlebot.game import Role
from whistlebot.hardware import (MOTOR_CARD, ConsoleMotors, LegoDoubleMotor,
                                 LegoLightSensor, SteadyLight, parse_card)
from whistlebot.hud import BAND_STYLE, Hud
from whistlebot.keys import bind_quit
from whistlebot.mqtt_link import MqttLink
from whistlebot.protocol import Event
from whistlebot.role_picker import RolePicker
from whistlebot.sensing import LightGuard


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", help="MQTT broker host (required unless --no-mqtt)")
    parser.add_argument("--port", type=int, default=1883)
    add_topic_args(parser)
    parser.add_argument("--motor-card", type=parse_card, default=MOTOR_CARD,
                        help="Double Motor connection card as color:serial "
                             "(default: blue:3685)")
    parser.add_argument("--sensor-card", type=parse_card,
                        help="Color Sensor card as color:serial, pre-filled in the popup")
    parser.add_argument("--dry-run", action="store_true",
                        help="print motor speeds instead of driving the LEGO motors")
    parser.add_argument("--calibration", type=Path,
                        default=Path(__file__).with_name("calibration.json"),
                        help="where whistle calibration is loaded from and saved to")
    parser.add_argument("--no-mqtt", action="store_true",
                        help="test mode: skip MQTT and start driving as soon as a role is picked")
    args = parser.parse_args()
    if not args.no_mqtt and not args.broker:
        parser.error("--broker is required unless --no-mqtt is given")
    return args


def describe(calibration):
    bands = "  ".join(f"{BAND_STYLE[c][0]} {lo:.0f}–{hi:.0f}"
                      for c, (lo, hi) in calibration.bands.items())
    return f"Whistle Hz: {bands}\nMin loudness: {calibration.min_rms:.0f}"


def main():
    args = parse_args()
    root = tk.Tk()
    root.withdraw()
    devices = []
    calibration = cal.load(args.calibration)

    # q quits from any window; what "quit" means depends on the phase.
    quitting = False

    def quit_setup():
        nonlocal quitting
        quitting = True
        for w in root.winfo_children():
            if isinstance(w, tk.Toplevel):
                w.destroy()

    on_quit = quit_setup
    bind_quit(root, lambda: on_quit())

    try:
        # 1. Connect to the bot.
        if args.dry_run:
            motors, status = ConsoleMotors(), "Dry run: no LEGO hardware"
        else:
            print(f"Connecting to Double Motor (card {args.motor_card[0]} {args.motor_card[1]})…")
            motors = LegoDoubleMotor(args.motor_card)
            devices.append(motors)
            status = f"✓ Connected to Double Motor ({args.motor_card[0]} {args.motor_card[1]})"

        # 2. Choose a role (or calibrate). The ball's light sensor connects
        #    from the popup; the mic is opened now so calibration can use it.
        mic, speaker = Microphone(), Speaker()
        devices.extend([mic, speaker])
        status += f"\nMic: {mic.name}"
        sensors = []

        def connect_sensor(card):
            sensors.append(LegoLightSensor(card))

        def run_calibration():
            nonlocal calibration
            monitor = cal.PitchMonitor(calibration)
            listener = ControlLoop(monitor, mic.read)
            listener.start()
            try:
                result = CalibrationWindow(root, calibration, monitor).show()
            finally:
                listener.stop()
            if result is None:
                return None
            calibration = result
            cal.save(calibration, args.calibration)
            print(f"Saved calibration to {args.calibration}")
            return describe(calibration)

        if args.no_mqtt:
            status += "  |  TEST MODE: no MQTT"
        picked = RolePicker(root, status, args.sensor_card,
                            need_sensor=not (args.dry_run or args.no_mqtt),
                            connect_sensor=None if args.dry_run else connect_sensor,
                            on_calibrate=run_calibration,
                            calibration_text=describe(calibration)).show()
        devices.extend(sensors)
        if picked is None or quitting:
            return
        role, _ = picked
        light = sensors[-1] if sensors else SteadyLight()

        # 3. Only now start listening and driving.
        app = BotApp(
            role=role,
            drive=Drive(motors),
            light=light,
            guard=LightGuard(),
            decoder=WhistleDecoder(calibration.bands),
            detector=calibration.detector(),
            publish=lambda payload: link.publish(payload) if link else
                print(f"[no-mqtt] would publish {payload!r}"),
            play=speaker.play,
        )
        if args.no_mqtt:
            link = None
            app.inbox.put(app.messages.encode(Event.START))  # start immediately
            print(f"{role.value} ready on mic '{mic.name}'; TEST MODE, whistle to drive")
        else:
            link = MqttLink(args.broker, on_payload=app.inbox.put, port=args.port,
                            topic=args.topic)
            link.start()
            print(f"{role.value} ready on mic '{mic.name}'; waiting for 'start' on {link.topic}")
        loop = ControlLoop(app, mic.read)
        loop.start()

        def shutdown():
            loop.stop()
            app.drive.halt()
            if link:
                link.stop()
            root.destroy()

        on_quit = shutdown
        Hud(root, app, loop, mic.name, on_close=shutdown,
            bands=calibration.bands, min_rms=calibration.min_rms)
        root.deiconify()
        root.mainloop()
    except Exception as exc:
        messagebox.showerror("whistle_bot", str(exc))
        raise
    finally:
        for device in reversed(devices):
            try:
                device.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
