"""
VIDUR Specs Module - Local Agent
Purpose: Standalone script (NOT part of the FastAPI server, run
separately by the user) that collects Specs telemetry on a configurable
interval and POSTs it to the backend's `POST /api/v1/specs/ingest`
route with the active `X-Project-Id` header. This is the only piece of
VIDUR that touches `psutil`, OS input hooks, or serial ports - the
backend itself never talks to hardware directly (CLAUDE.md Specs
Module: Data collection architecture).

Collected each cycle:
  - Computer: CPU%, RAM%, disk I/O (KB/s), internet latency (ms) - via
    `psutil` plus a lightweight TCP connect-timing check.
  - Personal: keyboard/mouse activity as aggregate-only event-count
    rates via `pynput` - counts events only, resets every cycle. Never
    logs key identity, key content, or continuous mouse coordinates.
  - Environmental: temperature/humidity/ambient light/noise level.
    Each cycle scans serial ports for a known Arduino/ESP32 USB
    VID:PID (see `KNOWN_BOARD_VID_PIDS`); on a match it requests one
    JSON reading over the line protocol documented in
    `docs/specs/serial-protocol.md` (`source: "hardware"`). No match,
    or a failed/malformed hardware read, falls back to a plausible
    simulated reading (`source: "simulation"`) - zero code changes are
    needed when real hardware is plugged in.

Any metric this agent has no data for is sent as `null`/omitted, which
the backend stores as `status: "missing"` - never fabricated.

Usage:
    python scripts/local_agent.py --project-id my-project --backend-url http://localhost:8080

    # or via environment variables instead of flags
    set VIDUR_PROJECT_ID=my-project
    set VIDUR_BACKEND_URL=http://localhost:8000
    python scripts/local_agent.py

    # optional tuning
    python scripts/local_agent.py --project-id my-project --interval 15 --log-level DEBUG

Install this script's dependencies separately from the backend server:
    pip install -r scripts/requirements-agent.txt
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Sequence, Tuple

import psutil
import serial
from pynput import keyboard, mouse
from serial.tools import list_ports as serial_list_ports

logger = logging.getLogger("vidur.local_agent")

DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_INTERVAL_SECONDS = 30.0
PROJECT_ID_HEADER = "X-Project-Id"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0
DEFAULT_LATENCY_HOST = "8.8.8.8"
DEFAULT_LATENCY_PORT = 53
DEFAULT_LATENCY_TIMEOUT_SECONDS = 2.0
DEFAULT_SERIAL_BAUDRATE = 115200
DEFAULT_SERIAL_TIMEOUT_SECONDS = 2.0
INGEST_PATH = "/api/v1/specs/ingest"

# Known Arduino/ESP32 USB VID:PID pairs, per docs/specs/serial-protocol.md.
KNOWN_BOARD_VID_PIDS: Dict[Tuple[int, int], str] = {
    (0x1A86, 0x7523): "CH340",
    (0x10C4, 0xEA60): "CP210x",
    (0x2341, 0x0043): "Arduino Uno",
    (0x2341, 0x0042): "Arduino Mega 2560",
    (0x0403, 0x6001): "Arduino Nano (FTDI)",
    (0x1A86, 0x55D3): "CH9102 (ESP32-S3)",
}

_ENVIRONMENTAL_METRIC_KEYS: Tuple[str, ...] = (
    "temperature_celsius",
    "humidity_percent",
    "ambient_light_lux",
    "noise_level_db",
)

# Plausible ranges used only when no hardware reading is available.
_SIMULATION_RANGES: Dict[str, Tuple[float, float]] = {
    "temperature_celsius": (18.0, 30.0),
    "humidity_percent": (30.0, 70.0),
    "ambient_light_lux": (0.0, 1000.0),
    "noise_level_db": (30.0, 70.0),
}


@dataclass
class AgentConfig:
    """Resolved configuration for one agent run."""

    project_id: str
    backend_url: str = DEFAULT_BACKEND_URL
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
    latency_host: str = DEFAULT_LATENCY_HOST
    latency_port: int = DEFAULT_LATENCY_PORT
    latency_timeout_seconds: float = DEFAULT_LATENCY_TIMEOUT_SECONDS
    serial_baudrate: int = DEFAULT_SERIAL_BAUDRATE
    serial_timeout_seconds: float = DEFAULT_SERIAL_TIMEOUT_SECONDS


def parse_args(argv: Optional[Sequence[str]] = None) -> AgentConfig:
    """Parse CLI args (falling back to environment variables) into an AgentConfig."""

    parser = argparse.ArgumentParser(
        prog="local_agent.py",
        description=(
            "VIDUR Specs local agent - collects computer/personal/environmental "
            "telemetry and POSTs it to the Specs ingestion API on an interval."
        ),
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("VIDUR_PROJECT_ID"),
        help="Active VIDUR project ID (or set VIDUR_PROJECT_ID)",
    )
    parser.add_argument(
        "--backend-url",
        default=os.environ.get("VIDUR_BACKEND_URL", DEFAULT_BACKEND_URL),
        help=f"Base URL of the VIDUR backend (or set VIDUR_BACKEND_URL). Default: {DEFAULT_BACKEND_URL}",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.environ.get("VIDUR_AGENT_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS)),
        help=f"Seconds between ingestion cycles. Default: {DEFAULT_INTERVAL_SECONDS}",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        help="HTTP request timeout in seconds for each ingest POST",
    )
    parser.add_argument(
        "--latency-host",
        default=DEFAULT_LATENCY_HOST,
        help="Host used for the internet latency connect-timing check",
    )
    parser.add_argument(
        "--latency-port",
        type=int,
        default=DEFAULT_LATENCY_PORT,
        help="Port used for the internet latency connect-timing check",
    )
    parser.add_argument(
        "--serial-baudrate",
        type=int,
        default=DEFAULT_SERIAL_BAUDRATE,
        help="Baud rate used when reading from matched hardware",
    )
    parser.add_argument(
        "--serial-timeout",
        type=float,
        default=DEFAULT_SERIAL_TIMEOUT_SECONDS,
        help="Serial read timeout in seconds before falling back to simulation",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )

    args = parser.parse_args(argv)

    if not args.project_id:
        parser.error("--project-id is required (or set the VIDUR_PROJECT_ID environment variable)")

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    return AgentConfig(
        project_id=args.project_id,
        backend_url=args.backend_url,
        interval_seconds=args.interval,
        request_timeout_seconds=args.request_timeout,
        latency_host=args.latency_host,
        latency_port=args.latency_port,
        serial_baudrate=args.serial_baudrate,
        serial_timeout_seconds=args.serial_timeout,
    )


# --------------------------------------------------------------------------
# Personal metrics (aggregate-only activity counts via pynput)
# --------------------------------------------------------------------------


class ActivityCounters:
    """Thread-safe aggregate-only keyboard/mouse event counters.

    Only counts are ever stored - never key identity, key content, or
    mouse coordinates (CLAUDE.md Specs Module: Personal).
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._key_press_count = 0
        self._mouse_event_count = 0
        self._last_reset = self._clock()

    def on_key_press(self, key: object = None) -> None:
        with self._lock:
            self._key_press_count += 1

    def on_mouse_move(self, x: object = None, y: object = None) -> None:
        with self._lock:
            self._mouse_event_count += 1

    def on_mouse_click(
        self, x: object = None, y: object = None, button: object = None, pressed: object = None
    ) -> None:
        with self._lock:
            self._mouse_event_count += 1

    def reset_and_read(self) -> Tuple[int, int, float]:
        """Return (key_press_count, mouse_event_count, elapsed_seconds) since the last reset, then reset."""

        with self._lock:
            now = self._clock()
            elapsed = max(now - self._last_reset, 0.0)
            key_presses = self._key_press_count
            mouse_events = self._mouse_event_count
            self._key_press_count = 0
            self._mouse_event_count = 0
            self._last_reset = now
        return key_presses, mouse_events, elapsed


def start_activity_listeners(
    counters: ActivityCounters,
    keyboard_listener_cls: Callable[..., object] = keyboard.Listener,
    mouse_listener_cls: Callable[..., object] = mouse.Listener,
) -> Tuple[object, object]:
    """Start (and return) daemon keyboard/mouse listeners wired to `counters`.

    Callback lambdas discard every argument except the fact that an
    event occurred - key identity and mouse coordinates never reach
    `counters` or anything else.
    """

    kb_listener = keyboard_listener_cls(on_press=lambda key: counters.on_key_press())
    ms_listener = mouse_listener_cls(
        on_move=lambda x, y: counters.on_mouse_move(),
        on_click=lambda x, y, button, pressed: counters.on_mouse_click(),
    )
    kb_listener.start()
    ms_listener.start()
    return kb_listener, ms_listener


def compute_rate_per_minute(count: int, elapsed_seconds: float) -> float:
    if elapsed_seconds <= 0:
        return 0.0
    return (count / elapsed_seconds) * 60.0


def build_personal_payload(
    key_press_count: int, mouse_event_count: int, elapsed_seconds: float
) -> Dict[str, Optional[float]]:
    """Build the `personal` ingest section. Fields this agent cannot
    measure (manual inputs, session duration, break frequency) are sent
    as `None` so the backend marks them missing rather than fabricating
    a value."""

    return {
        "last_session_duration_minutes": None,
        "sleep_hours": None,
        "caffeine_intake_mg": None,
        "typing_speed_cpm": round(compute_rate_per_minute(key_press_count, elapsed_seconds), 2),
        "mouse_activity_rate": round(compute_rate_per_minute(mouse_event_count, elapsed_seconds), 2),
        "break_frequency_per_hour": None,
    }


# --------------------------------------------------------------------------
# Computer metrics (psutil + a lightweight latency check)
# --------------------------------------------------------------------------


def measure_latency_ms(
    host: str,
    port: int,
    timeout: float,
    connector: Callable[..., "socket.socket"] = socket.create_connection,
) -> Optional[float]:
    """Time a bare TCP connect to (host, port). Returns None on failure."""

    start = time.monotonic()
    try:
        connection = connector((host, port), timeout=timeout)
        connection.close()
    except OSError:
        logger.warning("Latency check to %s:%s failed", host, port)
        return None
    return round((time.monotonic() - start) * 1000.0, 2)


class ComputerMetricsCollector:
    """Collects CPU/RAM/disk-IO/latency each cycle via injectable psutil
    and clock dependencies, so it can be unit tested without touching
    the real OS. Disk I/O is a rate, so it needs a baseline from the
    previous cycle - the first cycle reports it as missing (`None`)."""

    def __init__(self, psutil_module: object = psutil, clock: Callable[[], float] = time.monotonic) -> None:
        self._psutil = psutil_module
        self._clock = clock
        self._prev_disk_io_bytes: Optional[int] = None
        self._prev_disk_io_time: Optional[float] = None
        # Prime psutil's internal CPU-percent baseline; the result of this
        # first call is meaningless per psutil's own docs and is discarded.
        self._psutil.cpu_percent(interval=None)

    def collect(
        self,
        latency_host: str = DEFAULT_LATENCY_HOST,
        latency_port: int = DEFAULT_LATENCY_PORT,
        latency_timeout: float = DEFAULT_LATENCY_TIMEOUT_SECONDS,
        latency_fn: Callable[[str, int, float], Optional[float]] = measure_latency_ms,
    ) -> Dict[str, Optional[float]]:
        return {
            "cpu_usage_percent": self._safe_metric(lambda: self._psutil.cpu_percent(interval=None)),
            "ram_usage_percent": self._safe_metric(lambda: self._psutil.virtual_memory().percent),
            "disk_io_kbps": self._collect_disk_io_kbps(),
            "internet_latency_ms": latency_fn(latency_host, latency_port, latency_timeout),
        }

    def _safe_metric(self, fn: Callable[[], float]) -> Optional[float]:
        try:
            return round(float(fn()), 2)
        except Exception:
            logger.exception("Failed to collect a computer metric")
            return None

    def _collect_disk_io_kbps(self) -> Optional[float]:
        try:
            counters = self._psutil.disk_io_counters()
        except Exception:
            logger.exception("Failed to read disk IO counters")
            return None
        if counters is None:
            return None

        now = self._clock()
        total_bytes = counters.read_bytes + counters.write_bytes

        result: Optional[float] = None
        if self._prev_disk_io_bytes is not None and self._prev_disk_io_time is not None:
            elapsed = now - self._prev_disk_io_time
            if elapsed > 0:
                delta_bytes = max(total_bytes - self._prev_disk_io_bytes, 0)
                result = round(delta_bytes / elapsed / 1024.0, 2)

        self._prev_disk_io_bytes = total_bytes
        self._prev_disk_io_time = now
        return result


# --------------------------------------------------------------------------
# Environmental metrics (serial hardware handoff with simulation fallback)
# --------------------------------------------------------------------------


def find_known_serial_port(
    list_ports_fn: Callable[[], Sequence[object]] = serial_list_ports.comports,
) -> Optional[Tuple[str, str]]:
    """Scan serial ports for a known Arduino/ESP32 VID:PID. Returns
    (device_path, board_name) for the first match, or None."""

    for port in list_ports_fn():
        vid = getattr(port, "vid", None)
        pid = getattr(port, "pid", None)
        if vid is None or pid is None:
            continue
        board_name = KNOWN_BOARD_VID_PIDS.get((vid, pid))
        if board_name is not None:
            return port.device, board_name
    return None


def read_hardware_environmental_line(
    device: str,
    baudrate: int = DEFAULT_SERIAL_BAUDRATE,
    timeout: float = DEFAULT_SERIAL_TIMEOUT_SECONDS,
    serial_cls: Callable[..., object] = serial.Serial,
) -> Optional[str]:
    """Request and read one line per docs/specs/serial-protocol.md.
    Returns None on any I/O failure, timeout, or empty read."""

    try:
        with serial_cls(device, baudrate=baudrate, timeout=timeout) as connection:
            connection.reset_input_buffer()
            connection.write(b"READ\n")
            connection.flush()
            raw_line = connection.readline()
    except Exception:
        logger.warning("Serial read from %s failed", device, exc_info=True)
        return None

    if not raw_line:
        return None
    try:
        return raw_line.decode("utf-8").strip()
    except UnicodeDecodeError:
        return None


def parse_environmental_line(line: str) -> Optional[Dict[str, Optional[float]]]:
    """Parse one serial-protocol JSON line. A key the firmware omitted
    means that sensor is absent - reported as None (missing), never
    fabricated. Returns None (triggering the simulation fallback) if
    the line is not valid JSON or not a flat object."""

    try:
        payload = json.loads(line)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None

    reading: Dict[str, Optional[float]] = {}
    for key in _ENVIRONMENTAL_METRIC_KEYS:
        value = payload.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            reading[key] = float(value)
        else:
            reading[key] = None
    return reading


def simulate_environmental_reading(rng: "random.Random" = random) -> Dict[str, float]:
    """Generate plausible simulated readings for every environmental
    metric. Used only when no hardware is present or the hardware read
    failed - always marked source: simulation by the caller."""

    return {key: round(rng.uniform(*bounds), 2) for key, bounds in _SIMULATION_RANGES.items()}


def collect_environmental_metrics(
    list_ports_fn: Callable[[], Sequence[object]] = serial_list_ports.comports,
    serial_cls: Callable[..., object] = serial.Serial,
    baudrate: int = DEFAULT_SERIAL_BAUDRATE,
    serial_timeout: float = DEFAULT_SERIAL_TIMEOUT_SECONDS,
    rng: "random.Random" = random,
) -> Dict[str, object]:
    """Scan -> read -> parse -> simulate-on-failure, per CLAUDE.md's
    "simulation with automatic hardware handoff" contract. Always
    returns all four metric keys plus `source`."""

    match = find_known_serial_port(list_ports_fn)
    if match is not None:
        device, board_name = match
        line = read_hardware_environmental_line(
            device, baudrate=baudrate, timeout=serial_timeout, serial_cls=serial_cls
        )
        reading = parse_environmental_line(line) if line is not None else None
        if reading is not None:
            logger.info("Environmental reading from hardware (%s on %s)", board_name, device)
            reading["source"] = "hardware"
            return reading
        logger.warning(
            "Matched board %s on %s but the hardware read failed; falling back to simulation",
            board_name,
            device,
        )

    simulated: Dict[str, object] = dict(simulate_environmental_reading(rng))
    simulated["source"] = "simulation"
    return simulated


# --------------------------------------------------------------------------
# Payload assembly and transport
# --------------------------------------------------------------------------


def build_ingest_payload(
    personal: Dict[str, Optional[float]],
    computer: Dict[str, Optional[float]],
    environmental: Dict[str, object],
) -> Dict[str, Dict[str, object]]:
    """Assemble the request body matching `SpecsIngestRequest`'s shape."""

    return {"personal": personal, "computer": computer, "environmental": environmental}


def post_ingest(
    payload: Dict[str, object],
    backend_url: str,
    project_id: str,
    timeout: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    opener: Callable[..., object] = urllib.request.urlopen,
) -> bool:
    """POST one ingest payload. Returns True on a successful (2xx)
    response, False on any failure - callers should not crash the loop
    over a single failed cycle, since the next cycle will simply retry."""

    url = backend_url.rstrip("/") + INGEST_PATH
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            PROJECT_ID_HEADER: project_id,
        },
    )
    try:
        with opener(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            logger.info("Ingested Specs cycle: HTTP %s", status)
            return 200 <= status < 300
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error("Ingest rejected by backend: HTTP %s %s", exc.code, body)
        return False
    except urllib.error.URLError:
        logger.error("Could not reach backend at %s", url, exc_info=True)
        return False


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------


def run_cycle(
    config: AgentConfig,
    computer_collector: ComputerMetricsCollector,
    activity_counters: ActivityCounters,
    post_fn: Callable[..., bool] = post_ingest,
) -> bool:
    """Collect all three telemetry sections and POST one ingest cycle."""

    key_presses, mouse_events, elapsed = activity_counters.reset_and_read()
    personal = build_personal_payload(key_presses, mouse_events, elapsed)
    computer = computer_collector.collect(
        latency_host=config.latency_host,
        latency_port=config.latency_port,
        latency_timeout=config.latency_timeout_seconds,
    )
    environmental = collect_environmental_metrics(
        baudrate=config.serial_baudrate,
        serial_timeout=config.serial_timeout_seconds,
    )
    payload = build_ingest_payload(personal, computer, environmental)
    return post_fn(payload, config.backend_url, config.project_id, timeout=config.request_timeout_seconds)


def main(argv: Optional[Sequence[str]] = None) -> int:
    config = parse_args(argv)

    activity_counters = ActivityCounters()
    keyboard_listener, mouse_listener = start_activity_listeners(activity_counters)
    computer_collector = ComputerMetricsCollector()

    logger.info(
        "VIDUR local agent starting: project=%s backend=%s interval=%ss",
        config.project_id,
        config.backend_url,
        config.interval_seconds,
    )

    try:
        while True:
            cycle_start = time.monotonic()
            try:
                run_cycle(config, computer_collector, activity_counters)
            except Exception:
                logger.exception("Ingestion cycle failed; will retry next interval")
            elapsed = time.monotonic() - cycle_start
            time.sleep(max(config.interval_seconds - elapsed, 0.0))
    except KeyboardInterrupt:
        logger.info("Shutdown requested, stopping activity listeners")
    finally:
        keyboard_listener.stop()
        mouse_listener.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
