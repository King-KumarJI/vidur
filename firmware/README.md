# VIDUR Environmental Sensor Firmware (ESP32)

Firmware for the Specs Module's environmental metrics (Constitution
Chapter VII / `CLAUDE.md`'s IoT clause). Implements the exact serial
protocol documented in `../docs/specs/serial-protocol.md`, which
`backend/scripts/local_agent.py`'s hardware read path already expects —
no changes to `local_agent.py` are needed to use this firmware.

## Verification status (read this first)

**Compile-verified only. NOT hardware-verified.** No physical ESP32,
DHT22, BH1750, or sound sensor module was available when this firmware
was written, per VIDUR Constitution Article 50-51 (No Fake Completion
Law). What has actually been done:

- `pio run` succeeds against the `esp32dev` target (real Espressif32
  toolchain, real `DHT sensor library`/`Adafruit Unified Sensor`/`BH1750`
  dependencies resolved and linked — not a stub build).
- The JSON output shape was reviewed field-by-field against
  `../docs/specs/serial-protocol.md`'s schema (see "Protocol
  conformance" below).

What has **not** been done, and must happen before this firmware is
trusted: flashing to a real board, verifying each sensor reads
correct/plausible values, verifying the DHT22's timing-sensitive digital
protocol actually works over a real wire run, and verifying the sound
sensor's calibration approximation is anywhere close to reasonable for
the specific module used. Do not update the tracker or this file to say
"verified" until that has actually happened on real hardware.

## Hardware

- 1x ESP32 dev board (any common "ESP32 DevKit" / "NodeMCU-32S" style
  board using either a CP2102/CP210x or CH340 USB-serial chip — both are
  in `local_agent.py`'s `KNOWN_BOARD_VID_PIDS` table already).
- 1x DHT22 (AM2302) temperature/humidity sensor.
- 1x BH1750 ambient light sensor breakout (I2C, e.g. a GY-30/GY-302
  board).
- 1x analog sound sensor module (electret microphone + op-amp/comparator
  breakout with an analog output pin — e.g. a common "KY-038"-style
  module used in analog mode).
- 1x 10kΩ resistor (DHT22 data-line pull-up, unless your specific DHT22
  breakout already includes one on-board — most 3-pin breakout modules
  do; the bare 4-pin sensor does not).

## Wiring

| Sensor / signal          | ESP32 pin      | Notes                                                        |
|---------------------------|----------------|----------------------------------------------------------------|
| DHT22 VCC                 | 3V3            |                                                                  |
| DHT22 GND                 | GND            |                                                                  |
| DHT22 DATA                | GPIO4          | Needs a 10kΩ pull-up to 3V3 if not already on the breakout.     |
| BH1750 VCC                | 3V3            |                                                                  |
| BH1750 GND                | GND            |                                                                  |
| BH1750 SDA                | GPIO21         | ESP32 Arduino core's default I2C SDA pin.                      |
| BH1750 SCL                | GPIO22         | ESP32 Arduino core's default I2C SCL pin.                      |
| BH1750 ADDR                | GND (or leave floating) | Selects the library's default I2C address (0x23).   |
| Sound sensor VCC          | 3V3 or 5V      | Check your specific module's supply voltage rating.             |
| Sound sensor GND          | GND            |                                                                  |
| Sound sensor analog OUT   | GPIO34         | ADC1, input-only pin — safe to read regardless of Wi-Fi/ADC2 use. |

Pin assignments live at the top of `src/main.cpp` — change the
`constexpr` pin definitions there if your wiring differs.

## PlatformIO setup

This project is built with [PlatformIO](https://platformio.org/) (not
the Arduino IDE), so it can be built headlessly from the command line —
this is how it was compile-verified in this session, with no board
attached.

Install PlatformIO's CLI into its own isolated virtual environment,
separate from `backend/venv/` (the FastAPI app's environment) — it's a
firmware build tool, not a Python application dependency, so it does not
belong in `backend/requirements.txt`:

```bash
cd firmware
python -m venv .pio-venv

# Windows
.pio-venv\Scripts\activate.bat
# macOS/Linux
source .pio-venv/bin/activate

pip install platformio
```

Library dependencies (`adafruit/DHT sensor library`, `adafruit/Adafruit
Unified Sensor`, `claws/BH1750` — all free/open-source, no paid or
proprietary libraries) are declared in `platformio.ini`'s `lib_deps` and
are downloaded automatically by `pio run`; no separate install step is
needed.

## Build (no hardware required)

```bash
cd firmware
pio run
```

This compiles the firmware for the `esp32dev` board target and reports
flash/RAM usage. This step alone is what "compile-verified" means for
this firmware — it does not require a board to be connected.

## Flash (requires real hardware — not yet done)

Once a real ESP32 board is available:

1. Connect the ESP32 to your computer via USB.
2. Confirm the board's serial port is visible:
   ```bash
   pio device list
   ```
3. Flash:
   ```bash
   pio run --target upload
   ```
   PlatformIO auto-detects the port in most cases; if it picks the wrong
   one, pass it explicitly: `pio run --target upload --upload-port COM5`
   (Windows) or `--upload-port /dev/ttyUSB0` (Linux/macOS).
4. Confirm the firmware is answering the protocol correctly:
   ```bash
   pio device monitor --baud 115200
   ```
   then type `READ` and press Enter — you should see one line of JSON
   back, e.g. `{"temperature_celsius":24.3,"humidity_percent":41.0,"ambient_light_lux":310.5,"noise_level_db":38.2}`.
5. Once that's confirmed, `backend/scripts/local_agent.py` will pick the
   board up automatically on its next port scan — no agent-side
   configuration changes are needed, per the "zero code changes needed
   when hardware is plugged in" property `serial-protocol.md` documents.

## Protocol conformance

Reviewed field-by-field against `../docs/specs/serial-protocol.md`:

- **Transport:** `Serial.begin(115200)` — matches the documented 115200
  8N1 baud rate exactly (8N1 is the Arduino/ESP32 core's `Serial.begin`
  default framing).
- **Request:** the firmware only acts on an exact line equal to `READ`
  (`Serial.readStringUntil('\n')` + `.trim()`, which also strips a
  trailing `\r` for `\r\n`-terminated senders, matching "`\r\n`
  accepted, stripped on read"). Any other line is silently ignored, per
  "no other request verbs exist in this version of the protocol."
- **Response:** exactly one `\n`-terminated line of flat JSON
  (`Serial.println(...)`), containing only the four documented keys
  (`temperature_celsius`, `humidity_percent`, `ambient_light_lux`,
  `noise_level_db`) with numeric values, one decimal place each,
  matching the worked example in the spec.
- **Per-sensor presence:** each key is written into the response only if
  that sensor's read succeeded this cycle. DHT22 read failure (either
  value NaN) omits both `temperature_celsius` and `humidity_percent`
  together, since the library reports one combined digital read. BH1750
  read failure (negative return from `readLightLevel()`) omits
  `ambient_light_lux`. The sound sensor has no failure signal from
  `analogRead()`, so `noise_level_db` is always present on this board.
  No key is ever sent with a fabricated, zero, or stale value in place
  of a real reading — an omitted key is the only way this firmware
  represents "unavailable this cycle," exactly as the spec requires.
- **No unsolicited output:** `loop()` only calls `Serial.println` from
  inside the `READ`-handling branch — nothing is printed on boot or on
  any timer.

## Out of scope for this firmware

- A `MANIFEST` handshake distinguishing "this board never had this
  sensor" from "this sensor failed to read this cycle" — `serial-protocol.md`
  documents this as explicit future work (protocol v2), not implemented
  here or expected by the current `local_agent.py`.
- Sound sensor calibration against a real, lab-verified dB(SPL)
  reference. `src/main.cpp`'s `readNoiseLevelDb()` linearly maps the
  averaged raw ADC reading to an approximate 30–100 dB range as a
  documented placeholder approximation — real calibration requires a
  reference sound level meter and the specific sensor module in hand,
  neither of which exists in this environment yet.
