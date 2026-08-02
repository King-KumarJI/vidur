# VIDUR Environmental Sensor Firmware (ESP32 + Arduino Uno/Nano/Mega 2560)

Firmware for the Specs Module's environmental metrics (Constitution
Chapter VII / `CLAUDE.md`'s IoT clause, extended per Constitution
Article 19's requirement to support ESP32 AND the Arduino Uno/Nano/Mega
family). One shared codebase (`src/main.cpp`) implements the exact
serial protocol documented in `../docs/specs/serial-protocol.md`,
including the v1.1 `IDENTIFY` handshake addition, compiled for four
separate PlatformIO environments — `backend/scripts/local_agent.py`'s
hardware read path already expects this protocol; no changes to
`local_agent.py`'s wire contract were needed to use this firmware (its
detection *logic* was updated to use `IDENTIFY`, see "Board
identification handshake" below).

## Verification status (read this first)

**Compile-verified only, for all four board targets. NOT hardware-verified
on any of them.** No physical ESP32, Uno, Nano, Mega, DHT22, BH1750, or
sound sensor module was available when this firmware was written, per
VIDUR Constitution Article 50-51 (No Fake Completion Law). What has
actually been done:

- `pio run -e <environment>` succeeds for all four environments
  (`esp32dev`, `uno`, `nanoatmega328new`, `megaatmega2560`) — real
  toolchains (Xtensa for ESP32, avr-gcc for the AVR boards), real
  `DHT sensor library`/`Adafruit Unified Sensor`/`BH1750` dependencies
  resolved and linked for every target — not stub builds.
- The JSON output shape (both `READ`'s and `IDENTIFY`'s responses) was
  reviewed field-by-field against `../docs/specs/serial-protocol.md`'s
  schema (see "Protocol conformance" below).
- Uno/Nano's severe 2KB SRAM budget was checked directly against real
  compiler output (see "Compile results" below), not estimated.

What has **not** been done, and must happen before this firmware is
trusted on any board: flashing to real hardware, verifying each sensor
reads correct/plausible values, verifying the DHT22's timing-sensitive
digital protocol actually works over a real wire run on each board,
verifying I2C actually works on each board's specific SDA/SCL pins, and
verifying the sound sensor's calibration approximation is anywhere
close to reasonable for the specific module used. Do not update the
tracker or this file to say "verified" until that has actually happened
on real hardware, for each board claimed as verified.

## Supported boards

One codebase, four PlatformIO environments:

| PlatformIO environment | Board                          | `IDENTIFY` reports |
|-------------------------|---------------------------------|---------------------|
| `esp32dev`               | Any generic ESP32 dev board (CP2102/CP210x or CH340 USB-serial chip) | `esp32`    |
| `uno`                     | Arduino Uno                     | `uno`                |
| `nanoatmega328new`        | Arduino Nano (new-bootloader ATmega328P — the common one on current boards) | `nano` |
| `megaatmega2560`          | Arduino Mega / Mega 2560        | `mega2560`           |

The sensor logic and the `READ`/`IDENTIFY` protocol handling in
`src/main.cpp` are identical across all four targets. `#ifdef` is used
only where the underlying hardware genuinely differs — see "Where
`#ifdef` is used, and why" below.

## Hardware (per board — same sensor set for all four)

- 1x board from the table above.
- 1x DHT22 (AM2302) temperature/humidity sensor.
- 1x BH1750 ambient light sensor breakout (I2C, e.g. a GY-30/GY-302
  board).
- 1x analog sound sensor module (electret microphone + op-amp/comparator
  breakout with an analog output pin — e.g. a common "KY-038"-style
  module used in analog mode).
- 1x 10kΩ resistor (DHT22 data-line pull-up, unless your specific DHT22
  breakout already includes one on-board — most 3-pin breakout modules
  do; the bare 4-pin sensor does not).

## Wiring (per board)

Pin assignments live at the top of `src/main.cpp` (`DHT_PIN`,
`I2C_SDA_PIN`/`I2C_SCL_PIN` on ESP32, `SOUND_ADC_PIN`) — change the
`constexpr` definitions there if your wiring differs. On AVR boards
(Uno/Nano/Mega), I2C pins are fixed in silicon and **not** configurable
in software; `Wire.begin()` is called with no arguments and the board
routes SDA/SCL to whichever physical pins its chip defines.

### ESP32

| Sensor / signal          | ESP32 pin      | Notes                                                        |
|---------------------------|----------------|------------------------------------------------------------------|
| DHT22 VCC                 | 3V3            |                                                                    |
| DHT22 GND                 | GND            |                                                                    |
| DHT22 DATA                | GPIO4          | Needs a 10kΩ pull-up to 3V3 if not already on the breakout.       |
| BH1750 VCC                | 3V3            |                                                                    |
| BH1750 GND                | GND            |                                                                    |
| BH1750 SDA                | GPIO21         | ESP32 Arduino core's default I2C SDA pin (configurable in code).  |
| BH1750 SCL                | GPIO22         | ESP32 Arduino core's default I2C SCL pin (configurable in code).  |
| BH1750 ADDR                | GND (or leave floating) | Selects the library's default I2C address (0x23).       |
| Sound sensor VCC          | 3V3 or 5V      | Check your specific module's supply voltage rating.               |
| Sound sensor GND          | GND            |                                                                    |
| Sound sensor analog OUT   | GPIO34         | ADC1, input-only pin — safe to read regardless of Wi-Fi/ADC2 use. |

### Arduino Uno / Nano

| Sensor / signal          | Uno/Nano pin   | Notes                                                        |
|---------------------------|----------------|------------------------------------------------------------------|
| DHT22 VCC                 | 5V (or 3V3 on 3.3V Nano variants) |                                                 |
| DHT22 GND                 | GND            |                                                                    |
| DHT22 DATA                | D4             | Needs a 10kΩ pull-up if not already on the breakout.              |
| BH1750 VCC                | 5V or 3V3 (check your breakout's regulator) |                                      |
| BH1750 GND                | GND            |                                                                    |
| BH1750 SDA                | **A4**         | Uno/Nano's I2C SDA pin — fixed in silicon, not configurable.      |
| BH1750 SCL                | **A5**         | Uno/Nano's I2C SCL pin — fixed in silicon, not configurable.      |
| BH1750 ADDR                | GND (or leave floating) | Selects the library's default I2C address (0x23).       |
| Sound sensor VCC          | 5V             |                                                                    |
| Sound sensor GND          | GND            |                                                                    |
| Sound sensor analog OUT   | **A0**         | Uno/Nano's 10-bit ADC.                                            |

### Arduino Mega / Mega 2560

| Sensor / signal          | Mega pin       | Notes                                                        |
|---------------------------|----------------|------------------------------------------------------------------|
| DHT22 VCC                 | 5V             |                                                                    |
| DHT22 GND                 | GND            |                                                                    |
| DHT22 DATA                | D4             | Needs a 10kΩ pull-up if not already on the breakout.              |
| BH1750 VCC                | 5V or 3V3 (check your breakout's regulator) |                                      |
| BH1750 GND                | GND            |                                                                    |
| BH1750 SDA                | **Pin 20**     | Mega's dedicated I2C SDA pin — fixed in silicon, not configurable.|
| BH1750 SCL                | **Pin 21**     | Mega's dedicated I2C SCL pin — fixed in silicon, not configurable.|
| BH1750 ADDR                | GND (or leave floating) | Selects the library's default I2C address (0x23).       |
| Sound sensor VCC          | 5V             |                                                                    |
| Sound sensor GND          | GND            |                                                                    |
| Sound sensor analog OUT   | **A0**         | Mega's 10-bit ADC (same pin as Uno/Nano; Mega has A0–A15 available). |

## Where `#ifdef` is used, and why

`src/main.cpp` uses exactly one architecture branch
(`#if defined(ARDUINO_ARCH_ESP32) ... #else ... #endif`), not one branch
per board, because Uno/Nano/Mega share identical *behavior* even though
their physical I2C pins differ:

- **I2C initialization**: ESP32's `Wire.begin(sda, scl)` takes explicit
  pin arguments (software-configurable routing); every AVR board's
  `Wire.begin()` takes none (SDA/SCL are fixed in silicon per chip —
  the pin *numbers* differ by board, per the wiring tables above, but
  the *code* calling `Wire.begin()` does not).
- **ADC resolution and the sound sensor pin**: ESP32's ADC is 12-bit
  (0–4095) on GPIO34; every AVR board's ADC is 10-bit (0–1023) on A0.
  `ADC_MAX_VALUE`/`SOUND_ADC_PIN` are set once per architecture branch.

Per-board *identity* (which of the three AVR boards this is, for the
`IDENTIFY` response) does **not** use `#ifdef` at all — it comes from
`VIDUR_BOARD_ID`, a `-D` build flag set explicitly per PlatformIO
environment in `platformio.ini`, so the environment → board-name mapping
lives in exactly one, easily auditable place rather than depending on
guessing which internal Arduino-core board macro each environment
defines.

## Board identification handshake (`IDENTIFY`) — protocol v1.1

`docs/specs/serial-protocol.md` documents this as an explicit, flagged
addition (not a silent protocol change): a new `IDENTIFY\n` request,
answered with `{"board": "<id>"}` (`<id>` is `esp32`, `uno`, `nano`, or
`mega2560`). This lets `local_agent.py` confirm "this is real VIDUR
firmware, and which board" authoritatively, rather than inferring board
type from the USB-serial chip's VID:PID alone — CH340/CP210x/FTDI chips
are used by countless unrelated boards and devices, so a VID:PID match
by itself only means "something that might speak this protocol is
connected," not "VIDUR firmware is definitely running here."

`local_agent.py`'s detection logic now sends `IDENTIFY` to a
VID:PID-matched port before attempting a `READ`; only a confirmed
`IDENTIFY` response proceeds to `READ`, and an unanswered/malformed
`IDENTIFY` falls back to simulation for that cycle — the same graceful
fallback `READ` failures already used.

## PlatformIO setup

This project is built with [PlatformIO](https://platformio.org/) (not
the Arduino IDE), so it can be built headlessly from the command line —
this is how it was compile-verified in this session, with no board
attached for any of the four targets.

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
proprietary libraries) are declared once in `platformio.ini`'s shared
`[env]` section's `lib_deps` (applied to every board environment, not
copy-pasted per environment) and are downloaded automatically by
`pio run`; no separate install step is needed. All three libraries
support AVR natively (they were originally written for boards like the
Uno), so no library substitution was needed to add Uno/Nano/Mega
support.

## Build (no hardware required)

Build a single board target:

```bash
cd firmware
pio run -e esp32dev
pio run -e uno
pio run -e nanoatmega328new
pio run -e megaatmega2560
```

Or build all four in one command:

```bash
pio run
```

This is what "compile-verified" means for this firmware — it does not
require any board to be connected. The atmelavr platform (toolchain,
AVR Arduino core) is downloaded automatically on first use, the same
way espressif32 already was.

## Compile results (this session, all four targets — `[SUCCESS]`)

| Environment          | Board             | RAM used                          | Flash used                            |
|------------------------|--------------------|-------------------------------------|------------------------------------------|
| `esp32dev`              | ESP32              | 6.7% (22,024 / 327,680 bytes)       | 22.6% (296,113 / 1,310,720 bytes)         |
| `uno`                   | Arduino Uno        | **27.6% (566 / 2,048 bytes)**       | 36.3% (11,724 / 32,256 bytes)             |
| `nanoatmega328new`      | Arduino Nano       | **27.6% (566 / 2,048 bytes)**       | 38.2% (11,724 / 30,720 bytes)             |
| `megaatmega2560`        | Arduino Mega 2560  | 6.9% (566 / 8,192 bytes)            | 4.9% (12,570 / 253,952 bytes)              |

Uno/Nano's 2KB SRAM budget — the tightest constraint of the four boards
by a wide margin — is used well within safety margin (566 bytes, 27.6%),
leaving over 1.4KB of headroom for the Arduino runtime's own working
RAM (stack, `Serial` buffers, library internals) during operation. This
was achieved by avoiding the Arduino `String` class entirely in
`src/main.cpp` (see the "Uno/Nano RAM budget" note below) — using it
would have pulled in a heap allocator and risked fragmentation on a
2KB device with no way to observe or bound it statically.

## Flash (requires real hardware — not yet done, any board)

Once a real board is available, flashing any of the four is the same
process (only the environment name changes):

1. Connect the board to your computer via USB.
2. Confirm the board's serial port is visible:
   ```bash
   pio device list
   ```
3. Flash (example: Uno):
   ```bash
   pio run -e uno --target upload
   ```
   PlatformIO auto-detects the port in most cases; if it picks the wrong
   one, pass it explicitly: `pio run -e uno --target upload --upload-port COM5`
   (Windows) or `--upload-port /dev/ttyUSB0` (Linux/macOS).
4. Confirm the firmware is answering the protocol correctly:
   ```bash
   pio device monitor --baud 115200
   ```
   then type `IDENTIFY` and press Enter — you should see
   `{"board":"uno"}` (or the matching board id) back; then type `READ`
   and press Enter — you should see one line of JSON back, e.g.
   `{"temperature_celsius":24.3,"humidity_percent":41.0,"ambient_light_lux":310.5,"noise_level_db":38.2}`.
5. Once that's confirmed, `backend/scripts/local_agent.py` will pick the
   board up automatically on its next port scan (via `IDENTIFY`,
   confirming real firmware before it tries `READ`) — no agent-side
   configuration changes are needed, per the "zero code changes needed
   when hardware is plugged in" property `serial-protocol.md` documents.

## Protocol conformance

Reviewed field-by-field against `../docs/specs/serial-protocol.md`,
for every one of the four board targets (the code path is identical
across all of them except the two `#ifdef` branches documented above):

- **Transport:** `Serial.begin(115200)` — matches the documented 115200
  8N1 baud rate exactly on both the ESP32 and AVR Arduino cores.
- **Request parsing:** a fixed-size char buffer (`commandBuffer`, never
  Arduino `String`) accumulates incoming bytes until `\n`, strips a
  trailing `\r` (matching "`\r\n` accepted, stripped on read"), and
  compares the result with `strcmp()` against `READ`/`IDENTIFY`. Any
  other line — including one truncated by exceeding
  `COMMAND_BUFFER_SIZE` — is silently ignored, per "no other request
  verbs exist" (now: no other verbs besides `READ`/`IDENTIFY`).
- **`READ` response:** exactly one `\n`-terminated line of flat JSON
  (`Serial.println(...)`), containing only the four documented keys
  (`temperature_celsius`, `humidity_percent`, `ambient_light_lux`,
  `noise_level_db`) with numeric values, one decimal place each,
  matching the worked example in the spec.
- **`IDENTIFY` response:** exactly one `\n`-terminated line of flat
  JSON, `{"board": "<id>"}`, where `<id>` matches `VIDUR_BOARD_ID`'s
  compile-time value for that environment exactly (`esp32`, `uno`,
  `nano`, `mega2560`) — verified by inspection against each
  environment's `platformio.ini` build flag, one-to-one.
- **Per-sensor presence:** each key is written into the `READ` response
  only if that sensor's read succeeded this cycle — identical logic on
  every board target (DHT22 NaN → both `temperature_celsius`/
  `humidity_percent` omitted together; BH1750 negative return →
  `ambient_light_lux` omitted; the sound sensor has no failure signal
  from `analogRead()`, so `noise_level_db` is always present on every
  board). No key is ever sent with a fabricated, zero, or stale value
  in place of a real reading.
- **No unsolicited output:** `loop()` only calls `Serial.println` from
  inside the `READ`/`IDENTIFY`-handling branches — nothing is printed
  on boot or on any timer, on any board.

## Uno/Nano RAM budget (2KB — the tightest constraint of the four targets)

`src/main.cpp` deliberately avoids the Arduino `String` class for both
the request parser (`commandBuffer`, a fixed 16-byte `char[]`) and the
JSON response builder (`jsonBuffer`, a fixed 128-byte `char[]`, built
with `dtostrf()` + `snprintf()` rather than `String` concatenation).
`String` heap-allocates and can fragment an already-tiny 2KB heap over
many request/response cycles in a way that's difficult to bound or
observe on a device with no debugger attached in the field; fixed
stack buffers have a RAM cost that is exactly what `pio run`'s reported
`RAM: 566/2048 bytes` already accounts for, with no runtime surprises.

A related, AVR-specific gotcha this design avoids: the default Arduino
AVR toolchain's `snprintf()` does **not** support `%f` (floating-point
format specifiers) unless linked against `libprintf_flt`, which
PlatformIO's default AVR build does not do. `dtostrf()` (part of both
the AVR and ESP32 Arduino cores) converts each float to text first, so
`snprintf()` only ever needs to format `%s` (string) substitutions —
sidestepping that limitation entirely rather than working around it
with extra linker flags.

## Out of scope for this firmware

- A `MANIFEST` handshake distinguishing "this board never had this
  sensor" from "this sensor failed to read this cycle" — `serial-protocol.md`
  documents this as explicit future work (protocol v2), distinct from
  the `IDENTIFY` handshake implemented here, and not implemented or
  expected by the current `local_agent.py`.
- Sound sensor calibration against a real, lab-verified dB(SPL)
  reference. `src/main.cpp`'s `readNoiseLevelDb()` linearly maps the
  averaged raw ADC reading to an approximate 30–100 dB range as a
  documented placeholder approximation — real calibration requires a
  reference sound level meter and the specific sensor module in hand,
  neither of which exists in this environment yet, for any board.
- Board targets beyond the four listed above (e.g. Arduino Leonardo,
  ESP8266, other AVR variants) — not requested; `VIDUR_BOARD_ID`'s
  per-environment build flag pattern in `platformio.ini` makes adding
  another board target straightforward when one is actually needed.
