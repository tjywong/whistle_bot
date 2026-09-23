# whistle_bot

A LEGO Education robot for the ME193 World Cup, controlled by whistling. The laptop listens to the microphone, works out the whistle's pitch, and drives a LEGO Education **Double Motor** over Bluetooth. Robots coordinate over MQTT on the topic `ME193/Rogers`.

Each robot plays one of two roles:

- **Ball:** drive into the goal. When it gets there, a special **GOAL** whistle announces the goal. If the goalie gets close to the ball's light sensor, the ball has been caught.
- **Goalie:** stop the ball by getting close to the ball's light sensor.

Both robots play a victory or defeat song on the laptop speakers when a round ends.

---

## Setup

**Requirements:** macOS, Python 3.11+, and [Homebrew](https://brew.sh) (PyAudio needs PortAudio).

```sh
brew install portaudio
python3 -m venv venv
CFLAGS="-I/opt/homebrew/include" LDFLAGS="-L/opt/homebrew/lib" venv/bin/pip install -r requirements.txt
```

The `CFLAGS` / `LDFLAGS` tell pip where Homebrew keeps PortAudio. Without them, PyAudio fails to build.

**Hardware:**

- **Double Motor (required):** tap it with its Connection Card. The default card is **blue 3685**; use `--motor-card` for another.
- **Color Sensor (Ball only):** mount it open at the front of the car. By default it connects with the same card as the Double Motor, so tap the sensor with that card too.
- **Firmware:** if connecting prints *"needs a firmware update"*, update that device at <https://code.legoeducation.com/> in Chrome.

---

## Running

```sh
# Game day: class topic
venv/bin/python whistle_bot.py --broker broker.hivemq.com

# Solo testing on a private topic that classmates' robots don't hear
venv/bin/python whistle_bot.py --broker broker.hivemq.com --test-topic

# Drive by whistle with no MQTT at all (starts immediately)
venv/bin/python whistle_bot.py --no-mqtt

# No LEGO hardware: prints wheel speeds instead of driving
venv/bin/python whistle_bot.py --no-mqtt --dry-run
```

Startup order:

1. **Connect to the bot.** The program connects to the Double Motor.
2. **Pick a role.** A popup asks for **Ball** or **Goalie**. It also has **Calibrate whistle…**. Choosing Ball connects the Color Sensor.
3. **Play.** The HUD window opens. Whistles only drive the robot after a `start` message arrives. With `--no-mqtt`, driving starts straight away.

Press **q** in any window (or click **Quit**) to stop. This halts the motors and disconnects cleanly. Typing `q` in a text box doesn't quit.

| Option | Meaning |
|---|---|
| `--broker HOST` | MQTT broker (required unless `--no-mqtt`) |
| `--port N` | Broker port (default 1883) |
| `--topic T` / `--test-topic` | Topic to use. Default `ME193/Rogers`; the test topic is `ME193/Rogers/tyler-test` |
| `--motor-card color:serial` | Double Motor card (default `blue:3685`) |
| `--sensor-card color:serial` | Color Sensor card (default: same as the motor) |
| `--calibration PATH` | Calibration file (default `calibration.json`) |
| `--no-mqtt` | Skip MQTT and drive immediately |
| `--dry-run` | No LEGO hardware; print motor speeds |

### Choosing the microphone

The program uses whatever **System Settings → Sound → Input** is set to when it starts, for example the MacBook microphone or Bluetooth headphones. It doesn't follow changes while it's running, so quit and relaunch after switching. The HUD's **Mic:** line and the terminal's `ready on mic '…'` line show which microphone is in use.

Songs play on the **Output** device selected on the same settings page.

---

## Whistle controls

| Command | What the robot does |
|---|---|
| **Forward** | Drive forward at 100% |
| **Backward** | Drive backward at 100% |
| **Slower** | Take 20% off the speed, never below 20% |
| **Left / Right** | Turn: the inside wheel runs at 40%. When stopped, pivot in place |
| **Stop** | Stop; the next move defaults to forward |
| **GOAL** | *(Ball only)* announce a goal. Must be held about 0.7 s |

A command fires once the pitch has been held for about 0.2 s. A pitch between two ranges is ignored, and so is anything quiet or noisy that doesn't sound like a pure tone.

**Default pitch ranges** (used until you calibrate):

| Command | Range (Hz) |
|---|---|
| Stop | 600–900 |
| Backward | 900–1200 |
| Left | 1200–1500 |
| Right | 1500–1850 |
| Forward | 1850–2200 |
| Slower | 2200–3000 |
| GOAL | 3000–4500 |

---

## Calibrating your whistle

Click **Calibrate whistle…** in the startup popup:

1. **Measure noise.** Stay quiet for 2 s. This sets the loudness threshold to 3× the room's background noise, with a minimum of 2500.
2. **Record each command.** Click **Record** next to a command and whistle it steadily for 1.5 s. The command's range is centred on your pitch.
3. **Save.** This writes `calibration.json`, which is loaded on every start.

You can also type any low/high Hz values directly.

Tips:

- **Record all seven commands in one session.** Commands recorded in the same session are kept in place. A command you haven't recorded is moved out of the way if a new recording needs its space; its row then says *"moved: record it"*.
- **Whistles can be close together.** They can be as close as a half step (about 6%). Closer ranges need a steadier whistle.
- **Watch the HUD while testing.** The **HUD** FFT plot (800–3000 Hz) shades each command's range and draws a dashed line at your current pitch. The status line shows loudness against the threshold.
- **Recalibrate after switching microphones.** A different mic hears your whistle and the room very differently.

---

## MQTT messages

Agree these with your opponent before the match. They're defined in one place, [`MQTT.py`](MQTT.py).

| Message | Sent by | Meaning |
|---|---|---|
| `start` | Referee | Round begins; whistles now drive |
| `ball_caught` | Ball | The goalie reached the ball's light sensor. **Goalie wins** |
| `ball_scored` | Ball | The ball made it into the goal. **Ball wins** |

What each robot does:

| Role | Trigger | Result |
|---|---|---|
| Ball | Light sensor tripped | Stop, send `ball_caught`, play the defeat song |
| Ball | GOAL whistle | Stop, send `ball_scored`, play the victory song |
| Goalie | Receives `ball_caught` | Stop, play the victory song |
| Goalie | Receives `ball_scored` | Stop, play the defeat song |

Other behaviour:

- **Before `start`:** messages are ignored.
- **After the round ends:** messages are ignored, including the robot's own message echoed back by the broker.
- **New round:** a new `start` begins another round without restarting the program.
- **Logging:** every message the robot hears is printed in the terminal and shown on the HUD with what it did, for example `'ball_caught' -> ignored: round not started (send 'start' first)`.

---

## Testing without another robot

The referee window stands in for the referee and the opponent:

```sh
# Terminal 1: referee window with Start / Ball caught / Ball scored buttons and a live log
venv/bin/python MQTT.py --broker broker.hivemq.com --test-topic referee

# Terminal 2: the robot on the same private topic
venv/bin/python whistle_bot.py --broker broker.hivemq.com --test-topic
```

- **Always click Start first,** then end the round with a button (Goalie) or by whistling GOAL or covering the sensor (Ball).
- **Class topic warning:** the referee window shows a red banner if it's opened on the class topic.
- **Command-line helpers:**

  ```sh
  venv/bin/python MQTT.py --broker broker.hivemq.com --test-topic watch             # print all traffic
  venv/bin/python MQTT.py --broker broker.hivemq.com --test-topic start             # send start
  venv/bin/python MQTT.py --broker broker.hivemq.com --test-topic send ball_caught  # send anything
  ```

- **Privacy:** `broker.hivemq.com` is public. The test topic keeps classmates' robots (on `ME193/Rogers`) from reacting, but anyone who subscribes to it can still read it.

---

## Unit tests

```sh
venv/bin/python -m pytest -q
```

The tests cover every module with fakes, so no robot, microphone or broker is needed. The window tests are skipped if no display is available.

---

## Code layout

| File | Purpose |
|---|---|
| `whistle_bot.py` | Entry point: connect to the bot → role popup → MQTT, control loop, HUD |
| `MQTT.py` | Topic, agreed messages, MQTT client, and the `start/send/watch/referee` helper |
| `calibration.json` | Your saved whistle ranges and loudness threshold |
| `whistlebot/pitch.py` | FFT pitch detection, with sub-bin accuracy, and noise rejection |
| `whistlebot/commands.py` | Commands, per-command pitch ranges, debouncing |
| `whistlebot/calibration.py`, `calibration_ui.py` | Recording ranges, measuring noise, calibration window |
| `whistlebot/drive.py` | Speed, direction and steering → left/right wheel speeds |
| `whistlebot/hardware.py` | LEGO Double Motor and Color Sensor adapters, and dry-run stand-ins |
| `whistlebot/sensing.py` | Detects the goalie at the light sensor |
| `whistlebot/game.py` | Ball/goalie rules as a state machine (no hardware) |
| `whistlebot/protocol.py`, `mqtt_link.py` | Message decoding; MQTT client (re-exported from `MQTT.py`) |
| `whistlebot/app.py`, `control.py` | Ties everything together; background loop that reads audio |
| `whistlebot/hud.py`, `role_picker.py`, `referee.py`, `keys.py` | HUD, role popup, referee window, `q` to quit |
| `whistlebot/songs.py`, `audio_io.py` | Victory/defeat songs; PyAudio microphone and speaker |

### Motor wiring

The Double Motor's outputs are crossed on this robot: the motor's **left** output drives the car's **right** wheel. `LegoDoubleMotor` handles this with `swap_sides=True`. If you rebuild the robot:

- **The car drives backwards:** flip `left_reversed` and `right_reversed`.
- **Forward is right but turns are mirrored:** flip `swap_sides`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Robot ignores `ball_caught` / `ball_scored` | The round hasn't started. Send `start` first, and check that the HUD's MQTT line shows it |
| *"Could not find device matching Card …"* | Wrong card, or the device isn't on or freshly tapped. Every device answers to the card it was last tapped with |
| *"needs a firmware update"* | Update that device at <https://code.legoeducation.com/> |
| Phantom commands from room noise | Run **Measure noise** in calibration; keep gaps between ranges |
| Whistle not recognised | Whistle closer or louder, check that the HUD level is above the threshold, and recalibrate |
| Wrong microphone | Set **System Settings → Sound → Input**, then relaunch |
| No sound from songs | Check the Mac's **Output** device and volume |
