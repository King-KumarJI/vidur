# VIDUR Specs Module — Environmental Sensor Serial Protocol

**Status:** Documented for `backend/scripts/local_agent.py`'s hardware read path.
Firmware implementing this protocol is out of scope for this Python codebase
(VIDUR Constitution Article 40) — this document exists so that whoever writes
the Arduino/ESP32 firmware later has an exact contract to implement, requiring
**zero changes** to `local_agent.py` when real hardware is plugged in.

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
connected" — it is not proof the firmware is present or correct. A failed or
malformed read on a matched port is treated as a hardware read failure and the
agent falls back to simulation for that cycle (see `local_agent.py`'s
`collect_environmental_metrics`).

## Request/response cycle

Each ingestion cycle, after opening the port, the agent writes a single
request line and waits (bounded by a read timeout) for one response line:

```
Agent  -> Board:  READ\n
Board  -> Agent:  {"temperature_celsius": 24.3, "humidity_percent": 41.0, "ambient_light_lux": 310.5, "noise_level_db": 38.2}\n
```

- The request is the literal ASCII text `READ` followed by `\n`. No other
  request verbs exist in this version of the protocol.
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
  default 2.0 seconds). If no response line is received within the timeout,
  or the line is not valid JSON, or it parses to something other than a flat
  JSON object of numbers, the agent treats the entire cycle as a hardware
  read failure and falls back to simulated environmental data for that cycle
  only (source reported as `simulation`, not `hardware`).
- The agent does not retry within a cycle. The next ingestion cycle re-scans
  ports and re-attempts hardware communication from scratch — this is what
  gives the "zero code changes needed when hardware is plugged in" property:
  a board that was absent, mis-seated, or mid-reset on one cycle is simply
  tried again on the next.

## Future work (not implemented by `local_agent.py`, documented for later)

A future v2 of this protocol could add a `MANIFEST\n` request, answered once
on connect with a JSON object describing the board type and which sensors are
physically present, so the agent can distinguish "sensor omitted this reading
due to a transient fault" from "this board never had that sensor." Writing
that manifest handshake into firmware is explicitly out of scope for this
session (VIDUR Constitution Article 40 — no non-Python firmware code in this
codebase); `local_agent.py`'s per-field missing handling already works
correctly without it, so this is a future enhancement, not a blocker.
