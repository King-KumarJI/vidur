# VIDUR Specs Module — Environmental Sensor Serial Protocol

**Status:** Documented for `backend/scripts/local_agent.py`'s hardware read path.
Firmware implementing this protocol now exists (`firmware/`, ESP32 + Arduino
Uno/Nano/Mega 2560, compile-verified only — see `firmware/README.md`),
implementing this document exactly, including the v1.1 IDENTIFY handshake
addition below.

**Protocol version note (explicit, flagged addition — not a silent change):**
version 1.1 adds the `IDENTIFY` request/response pair documented in "Board
identification handshake" below. It is additive: every v1.0 behavior (`READ`
and its response, timeouts, per-sensor omission) is unchanged. `local_agent.py`
now tries `IDENTIFY` on a VID:PID-matched port as the authoritative "is this
real VIDUR firmware" check before attempting a `READ`, per the "Board
identification" section below.

## Transport

- USB CDC serial (the same port enumerated by `pyserial`'s `list_ports.comports()`).
- Baud rate: **115200 8N1**, no flow control.
- Line-based ASCII text. Every message — request or response — is exactly one
  line terminated by `\n` (`\r\n` accepted, stripped on read).

## Board identification (how the agent decides to try this protocol at all)

Before opening the port, the agent matches the port's USB VID:PID against a
known-boards table (see `local_agent.py`'s `KNOWN_BOARD_VID_PIDS`):

| Board / adapter chip        | VID:PID     |
|------------------------------|-------------|
| CH340 (common clone boards)  | `1A86:7523` |
| CP210x (ESP32 dev boards)    | `10C4:EA60` |
| Arduino Uno                  | `2341:0043` |
| Arduino Mega 2560             | `2341:0042` |
| Arduino Nano (FTDI-based)     | `0403:6001` |
| CH9102 (ESP32-S3 dev boards)  | `1A86:55D3` |

A VID:PID match only means "a board that plausibly speaks this protocol is
connected" — it is **not** proof the firmware is present or correct. These
USB-serial chips (CH340, CP210x, FTDI) ship on countless unrelated boards and
devices, so a VID:PID match alone cannot distinguish real VIDUR firmware from
some other device that happens to use the same USB-serial chip. This is why
the agent now treats VID:PID matching as a pre-filter only, and the
`IDENTIFY` handshake (below) as the authoritative confirmation. A failed or
malformed read on a matched, `IDENTIFY`-confirmed port is treated as a
hardware read failure and the agent falls back to simulation for that cycle
(see `local_agent.py`'s `collect_environmental_metrics`).

## Board identification handshake (`IDENTIFY`) — protocol v1.1 addition

Before requesting a `READ`, the agent sends the board a second, independent
request to confirm it is really running VIDUR firmware and to learn exactly
which board it's talking to:

```
Agent  -> Board:  IDENTIFY\n
Board  -> Agent:  {"board": "esp32"}\n
```

- The request is the literal ASCII text `IDENTIFY` followed by `\n` — same
  transport rules as `READ` (one line, `\n`-terminated, `\r\n` accepted and
  stripped).
- The response is a single line of flat JSON with exactly one key, `board`,
  whose value is one of the firmware's supported board identifiers:
  `"esp32"`, `"uno"`, `"nano"`, `"mega2560"` (see `firmware/platformio.ini`'s
  `VIDUR_BOARD_ID` build flag, one per environment — this is the
  authoritative, single place new board identifiers are added).
- A port that does not answer `IDENTIFY` within the timeout, or answers with
  something that is not valid JSON, not a flat object, or has no non-empty
  string `board` key, is **not** treated as confirmed VIDUR firmware — the
  agent does not attempt a `READ` on that port and falls back to simulation
  for that cycle, exactly as if the port had failed a `READ` (see "Timeouts
  and failure handling" below).
- `IDENTIFY` is answered from the same request/response loop as `READ` —
  firmware must not send anything unsolicited in response to it either.

## Request/response cycle

Each ingestion cycle, after opening the port, the agent writes a single
request line and waits (bounded by a read timeout) for one response line:

```
Agent  -> Board:  READ\n
Board  -> Agent:  {"temperature_celsius": 24.3, "humidity_percent": 41.0, "ambient_light_lux": 310.5, "noise_level_db": 38.2}\n
```

- The request is the literal ASCII text `READ` followed by `\n`. `READ` and
  `IDENTIFY` (above) are the only two request verbs defined by this protocol
  version; any other line is silently ignored by the firmware.
- The response is a single line of JSON — a flat object. Keys are exactly the
  four environmental metric names used by `EnvironmentalMetricsIngestRequest`:
  `temperature_celsius`, `humidity_percent`, `ambient_light_lux`,
  `noise_level_db`. Values are numbers (int or float).

## Per-sensor presence (missing sensors on the board)

A board does not have to carry all four sensors. **Any key the firmware
omits from the JSON object is treated as that sensor being absent** and is
reported by the agent as `status: "missing"` for that field only — the other,
present keys are still reported as `status: "hardware"`-sourced readings.
Firmware must never fabricate a value for a sensor it does not physically
have; omitting the key is the only correct way to represent that.

```
{"temperature_celsius": 24.3, "humidity_percent": 41.0}
```

is valid and means: this board has temperature and humidity sensors only;
ambient light and noise level are unavailable and will be marked missing.

## Timeouts and failure handling

- The agent's serial read timeout is configurable (`--serial-timeout`,
  default 2.0 seconds), and applies to `IDENTIFY` requests the same way it
  applies to `READ` requests. If no response line is received within the
  timeout, or the line is not valid JSON, or it parses to something other
  than the expected shape (a flat JSON object of numbers for `READ`; a flat
  JSON object with a non-empty string `board` key for `IDENTIFY`), the agent
  treats the cycle as a failure at that step. An `IDENTIFY` failure skips
  `READ` entirely for that port and falls back to simulated environmental
  data for that cycle only (source reported as `simulation`, not `hardware`).
- The agent does not retry within a cycle. The next ingestion cycle re-scans
  ports and re-attempts hardware communication (`IDENTIFY` then `READ`) from
  scratch — this is what gives the "zero code changes needed when hardware is
  plugged in" property: a board that was absent, mis-seated, or mid-reset on
  one cycle is simply tried again on the next.

## Future work (not implemented by `local_agent.py`, documented for later)

`IDENTIFY` (above) confirms firmware identity and board type but not
per-sensor presence. A future v2 of this protocol could extend `IDENTIFY`'s
response (or add a separate `MANIFEST\n` request) with a JSON array of which
sensors are physically present on this specific board, so the agent could
distinguish "sensor omitted this reading due to a transient fault" from "this
board never had that sensor." `local_agent.py`'s existing per-field missing
handling already works correctly without this distinction (both cases are
reported as `status: "missing"` today), so this remains a future enhancement,
not a blocker.
