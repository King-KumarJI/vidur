"""Unit tests for scripts/local_agent.py.

`local_agent.py` is a standalone script (not part of the FastAPI app),
so it is imported here by adding `backend/scripts` to `sys.path` rather
than via the `app` package. Every test that would otherwise touch a
real keyboard, mouse, serial port, or the network instead injects a
fake/stub dependency (matching this codebase's established DI-for-tests
pattern, e.g. `tests/unit/core/specs/test_storage.py`'s injectable
`database_provider`) - no real OS input hooks or hardware are required
to run this suite.
"""

import io
import json
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import local_agent  # noqa: E402  (import after sys.path manipulation, by necessity)


class _FakeClock:
    """Returns a fixed, pre-programmed sequence of monotonic values."""

    def __init__(self, values):
        self._values = list(values)

    def __call__(self):
        return self._values.pop(0)


# --------------------------------------------------------------------------
# Personal metrics
# --------------------------------------------------------------------------


class TestComputeRatePerMinute:
    def test_zero_elapsed_returns_zero(self):
        assert local_agent.compute_rate_per_minute(10, 0.0) == 0.0

    def test_negative_elapsed_returns_zero(self):
        assert local_agent.compute_rate_per_minute(10, -1.0) == 0.0

    def test_normal_rate(self):
        assert local_agent.compute_rate_per_minute(10, 30.0) == 20.0


class TestBuildPersonalPayload:
    def test_rates_computed_from_counts(self):
        payload = local_agent.build_personal_payload(key_press_count=120, mouse_event_count=30, elapsed_seconds=60.0)
        assert payload["typing_speed_cpm"] == 120.0
        assert payload["mouse_activity_rate"] == 30.0

    def test_unmeasured_fields_are_missing_not_fabricated(self):
        payload = local_agent.build_personal_payload(key_press_count=0, mouse_event_count=0, elapsed_seconds=10.0)
        assert payload["last_session_duration_minutes"] is None
        assert payload["sleep_hours"] is None
        assert payload["caffeine_intake_mg"] is None
        assert payload["break_frequency_per_hour"] is None


class TestActivityCounters:
    def test_reset_and_read_reports_counts_and_elapsed_then_resets(self):
        counters = local_agent.ActivityCounters(clock=_FakeClock([0.0, 10.0, 15.0]))
        counters.on_key_press(object())
        counters.on_key_press(object())
        counters.on_key_press(object())
        counters.on_mouse_move(123, 456)
        counters.on_mouse_click(1, 2, "left", True)

        key_presses, mouse_events, elapsed = counters.reset_and_read()
        assert key_presses == 3
        assert mouse_events == 2
        assert elapsed == 10.0

        # Counters must be zeroed after a read.
        key_presses_2, mouse_events_2, elapsed_2 = counters.reset_and_read()
        assert key_presses_2 == 0
        assert mouse_events_2 == 0
        assert elapsed_2 == 5.0

    def test_never_stores_key_identity_or_coordinates(self):
        counters = local_agent.ActivityCounters(clock=_FakeClock([0.0, 1.0]))
        counters.on_key_press(key="a")
        counters.on_mouse_move(x=999, y=999)
        # The only state ActivityCounters exposes is aggregate counts.
        assert vars(counters).keys() == {"_clock", "_lock", "_key_press_count", "_mouse_event_count", "_last_reset"}
        key_presses, mouse_events, _ = counters.reset_and_read()
        assert key_presses == 1
        assert mouse_events == 1


class _FakeListener:
    """Stand-in for pynput's keyboard/mouse Listener - captures the
    callbacks it was constructed with instead of hooking real OS input."""

    def __init__(self, **callbacks):
        self.callbacks = callbacks
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class TestStartActivityListeners:
    def test_wires_callbacks_and_starts_listeners(self):
        counters = local_agent.ActivityCounters(clock=_FakeClock([0.0, 1.0]))
        kb_listener, ms_listener = local_agent.start_activity_listeners(
            counters, keyboard_listener_cls=_FakeListener, mouse_listener_cls=_FakeListener
        )

        assert kb_listener.started is True
        assert ms_listener.started is True

        # Simulate real events firing through the injected fake listeners.
        kb_listener.callbacks["on_press"](key=object())
        ms_listener.callbacks["on_move"](50, 60)
        ms_listener.callbacks["on_click"](50, 60, "left", True)

        key_presses, mouse_events, _ = counters.reset_and_read()
        assert key_presses == 1
        assert mouse_events == 2


# --------------------------------------------------------------------------
# Computer metrics
# --------------------------------------------------------------------------


class TestMeasureLatencyMs:
    def test_success_returns_nonnegative_float(self):
        class _FakeSocket:
            def close(self):
                pass

        def _connector(address, timeout):
            return _FakeSocket()

        result = local_agent.measure_latency_ms("example.invalid", 443, 1.0, connector=_connector)
        assert isinstance(result, float)
        assert result >= 0.0

    def test_failure_returns_none(self):
        def _connector(address, timeout):
            raise OSError("unreachable")

        result = local_agent.measure_latency_ms("example.invalid", 443, 1.0, connector=_connector)
        assert result is None


class _FakePsutil:
    def __init__(self, cpu_values, ram_percent=50.0, disk_io_sequence=None, raise_on_ram=False):
        self._cpu_values = list(cpu_values)
        self._ram_percent = ram_percent
        self._disk_io_sequence = list(disk_io_sequence) if disk_io_sequence is not None else []
        self._raise_on_ram = raise_on_ram

    def cpu_percent(self, interval=None):
        return self._cpu_values.pop(0)

    def virtual_memory(self):
        if self._raise_on_ram:
            raise RuntimeError("boom")
        return SimpleNamespace(percent=self._ram_percent)

    def disk_io_counters(self):
        return self._disk_io_sequence.pop(0)


class TestComputerMetricsCollector:
    def test_first_cycle_has_no_disk_io_baseline(self):
        fake_psutil = _FakePsutil(
            cpu_values=[0.0, 12.5],  # first value consumed by priming in __init__
            ram_percent=40.0,
            disk_io_sequence=[SimpleNamespace(read_bytes=1000, write_bytes=1000)],
        )
        collector = local_agent.ComputerMetricsCollector(psutil_module=fake_psutil, clock=_FakeClock([100.0]))

        result = collector.collect(latency_fn=lambda host, port, timeout: 42.5)

        assert result["cpu_usage_percent"] == 12.5
        assert result["ram_usage_percent"] == 40.0
        assert result["disk_io_kbps"] is None
        assert result["internet_latency_ms"] == 42.5

    def test_second_cycle_computes_disk_io_rate(self):
        first_total = 2_000
        delta_bytes = 3_072_000  # -> 100.0 KB/s over 30s
        fake_psutil = _FakePsutil(
            cpu_values=[0.0, 10.0, 20.0],
            ram_percent=50.0,
            disk_io_sequence=[
                SimpleNamespace(read_bytes=1000, write_bytes=1000),
                SimpleNamespace(read_bytes=1000 + delta_bytes // 2, write_bytes=1000 + delta_bytes // 2),
            ],
        )
        collector = local_agent.ComputerMetricsCollector(psutil_module=fake_psutil, clock=_FakeClock([100.0, 130.0]))

        first = collector.collect(latency_fn=lambda host, port, timeout: 10.0)
        second = collector.collect(latency_fn=lambda host, port, timeout: 10.0)

        assert first["disk_io_kbps"] is None
        assert second["disk_io_kbps"] == pytest.approx(100.0)
        assert first_total == 2_000  # sanity check on the fixture math above

    def test_disk_io_counters_returning_none_is_missing_not_fabricated(self):
        fake_psutil = _FakePsutil(cpu_values=[0.0, 1.0], disk_io_sequence=[None])
        collector = local_agent.ComputerMetricsCollector(psutil_module=fake_psutil, clock=_FakeClock([100.0]))

        result = collector.collect(latency_fn=lambda host, port, timeout: None)
        assert result["disk_io_kbps"] is None
        assert result["internet_latency_ms"] is None

    def test_metric_collection_failure_is_missing_not_raised(self):
        fake_psutil = _FakePsutil(cpu_values=[0.0, 5.0], disk_io_sequence=[None], raise_on_ram=True)
        collector = local_agent.ComputerMetricsCollector(psutil_module=fake_psutil, clock=_FakeClock([100.0]))

        result = collector.collect(latency_fn=lambda host, port, timeout: 1.0)
        assert result["cpu_usage_percent"] == 5.0
        assert result["ram_usage_percent"] is None


# --------------------------------------------------------------------------
# Environmental metrics
# --------------------------------------------------------------------------


class TestFindKnownSerialPort:
    def test_matches_known_vid_pid(self):
        ports = [
            SimpleNamespace(vid=0x0000, pid=0x0000, device="COM1"),
            SimpleNamespace(vid=0x1A86, pid=0x7523, device="COM5"),
        ]
        result = local_agent.find_known_serial_port(list_ports_fn=lambda: ports)
        assert result == ("COM5", "CH340")

    def test_no_match_returns_none(self):
        ports = [SimpleNamespace(vid=0x9999, pid=0x9999, device="COM1")]
        result = local_agent.find_known_serial_port(list_ports_fn=lambda: ports)
        assert result is None

    def test_ports_missing_vid_pid_are_skipped(self):
        ports = [SimpleNamespace(vid=None, pid=None, device="COM1")]
        result = local_agent.find_known_serial_port(list_ports_fn=lambda: ports)
        assert result is None

    def test_empty_port_list_returns_none(self):
        assert local_agent.find_known_serial_port(list_ports_fn=lambda: []) is None


class _FakeSerialContext:
    def __init__(self, parent):
        self._parent = parent

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def reset_input_buffer(self):
        pass

    def write(self, data):
        self._parent.write_calls.append(data)

    def flush(self):
        pass

    def readline(self):
        return self._parent.response_line


class _FakeSerial:
    """Callable stand-in for `serial.Serial` - constructing it returns a
    context manager instead of opening a real serial port."""

    def __init__(self, response_line=b"", raise_on_open=False):
        self.response_line = response_line
        self.raise_on_open = raise_on_open
        self.write_calls = []

    def __call__(self, device, baudrate, timeout):
        if self.raise_on_open:
            raise OSError("port unavailable")
        return _FakeSerialContext(self)


class TestReadHardwareEnvironmentalLine:
    def test_sends_read_request_and_returns_stripped_line(self):
        fake_serial = _FakeSerial(response_line=b'{"temperature_celsius": 24.3}\r\n')
        line = local_agent.read_hardware_environmental_line("COM5", serial_cls=fake_serial)
        assert line == '{"temperature_celsius": 24.3}'
        assert fake_serial.write_calls == [b"READ\n"]

    def test_open_failure_returns_none(self):
        fake_serial = _FakeSerial(raise_on_open=True)
        line = local_agent.read_hardware_environmental_line("COM5", serial_cls=fake_serial)
        assert line is None

    def test_empty_read_returns_none(self):
        fake_serial = _FakeSerial(response_line=b"")
        line = local_agent.read_hardware_environmental_line("COM5", serial_cls=fake_serial)
        assert line is None


class TestParseEnvironmentalLine:
    def test_full_reading_parses_all_fields(self):
        line = json.dumps(
            {
                "temperature_celsius": 24.3,
                "humidity_percent": 41.0,
                "ambient_light_lux": 310.5,
                "noise_level_db": 38.2,
            }
        )
        reading = local_agent.parse_environmental_line(line)
        assert reading == {
            "temperature_celsius": 24.3,
            "humidity_percent": 41.0,
            "ambient_light_lux": 310.5,
            "noise_level_db": 38.2,
        }

    def test_omitted_keys_are_missing_not_fabricated(self):
        line = json.dumps({"temperature_celsius": 24.3, "humidity_percent": 41.0})
        reading = local_agent.parse_environmental_line(line)
        assert reading["temperature_celsius"] == 24.3
        assert reading["humidity_percent"] == 41.0
        assert reading["ambient_light_lux"] is None
        assert reading["noise_level_db"] is None

    def test_non_numeric_value_is_missing(self):
        line = json.dumps({"temperature_celsius": "warm"})
        reading = local_agent.parse_environmental_line(line)
        assert reading["temperature_celsius"] is None

    def test_invalid_json_returns_none(self):
        assert local_agent.parse_environmental_line("not json") is None

    def test_non_object_json_returns_none(self):
        assert local_agent.parse_environmental_line("[1, 2, 3]") is None


class TestSimulateEnvironmentalReading:
    def test_all_metrics_present_and_within_plausible_ranges(self):
        import random

        reading = local_agent.simulate_environmental_reading(rng=random.Random(42))
        for key, (low, high) in local_agent._SIMULATION_RANGES.items():
            assert key in reading
            assert low <= reading[key] <= high


class TestCollectEnvironmentalMetrics:
    def test_no_hardware_match_falls_back_to_simulation(self):
        import random

        result = local_agent.collect_environmental_metrics(list_ports_fn=lambda: [], rng=random.Random(1))
        assert result["source"] == "simulation"
        for key in local_agent._ENVIRONMENTAL_METRIC_KEYS:
            assert result[key] is not None

    def test_successful_hardware_read_reports_hardware_source(self):
        ports = [SimpleNamespace(vid=0x1A86, pid=0x7523, device="COM5")]
        fake_serial = _FakeSerial(response_line=json.dumps({"temperature_celsius": 22.1}).encode("utf-8"))

        result = local_agent.collect_environmental_metrics(
            list_ports_fn=lambda: ports, serial_cls=fake_serial
        )
        assert result["source"] == "hardware"
        assert result["temperature_celsius"] == 22.1
        assert result["humidity_percent"] is None

    def test_matched_board_but_failed_read_falls_back_to_simulation(self):
        import random

        ports = [SimpleNamespace(vid=0x1A86, pid=0x7523, device="COM5")]
        fake_serial = _FakeSerial(raise_on_open=True)

        result = local_agent.collect_environmental_metrics(
            list_ports_fn=lambda: ports, serial_cls=fake_serial, rng=random.Random(2)
        )
        assert result["source"] == "simulation"

    def test_matched_board_but_malformed_json_falls_back_to_simulation(self):
        import random

        ports = [SimpleNamespace(vid=0x1A86, pid=0x7523, device="COM5")]
        fake_serial = _FakeSerial(response_line=b"not json\n")

        result = local_agent.collect_environmental_metrics(
            list_ports_fn=lambda: ports, serial_cls=fake_serial, rng=random.Random(3)
        )
        assert result["source"] == "simulation"


# --------------------------------------------------------------------------
# Payload assembly and transport
# --------------------------------------------------------------------------


class TestBuildIngestPayload:
    def test_assembles_three_sections(self):
        payload = local_agent.build_ingest_payload({"a": 1}, {"b": 2}, {"c": 3})
        assert payload == {"personal": {"a": 1}, "computer": {"b": 2}, "environmental": {"c": 3}}


class _FakeHttpResponse:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class TestPostIngest:
    def test_success_sends_expected_request(self):
        captured = {}

        def _fake_opener(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return _FakeHttpResponse(status=200)

        ok = local_agent.post_ingest(
            {"personal": {}}, "http://localhost:8000/", "my-project", timeout=5.0, opener=_fake_opener
        )

        assert ok is True
        request = captured["request"]
        assert request.full_url == "http://localhost:8000/api/v1/specs/ingest"
        assert request.get_method() == "POST"
        assert request.get_header("X-project-id") == "my-project"
        assert request.get_header("Content-type") == "application/json"
        assert json.loads(request.data.decode("utf-8")) == {"personal": {}}
        assert captured["timeout"] == 5.0

    def test_http_error_is_caught_and_returns_false(self):
        def _fake_opener(request, timeout):
            raise urllib.error.HTTPError(
                url="http://localhost:8000/api/v1/specs/ingest",
                code=403,
                msg="Forbidden",
                hdrs=None,
                fp=io.BytesIO(b"feature disabled"),
            )

        ok = local_agent.post_ingest({}, "http://localhost:8000", "my-project", opener=_fake_opener)
        assert ok is False

    def test_url_error_is_caught_and_returns_false(self):
        def _fake_opener(request, timeout):
            raise urllib.error.URLError("connection refused")

        ok = local_agent.post_ingest({}, "http://localhost:8000", "my-project", opener=_fake_opener)
        assert ok is False


# --------------------------------------------------------------------------
# CLI parsing
# --------------------------------------------------------------------------


class TestParseArgs:
    def test_parses_explicit_flags(self):
        config = local_agent.parse_args(
            ["--project-id", "proj-1", "--backend-url", "http://host:9000", "--interval", "5"]
        )
        assert config.project_id == "proj-1"
        assert config.backend_url == "http://host:9000"
        assert config.interval_seconds == 5.0

    def test_falls_back_to_environment_variables(self, monkeypatch):
        monkeypatch.setenv("VIDUR_PROJECT_ID", "env-project")
        monkeypatch.setenv("VIDUR_BACKEND_URL", "http://env-host:1234")
        config = local_agent.parse_args([])
        assert config.project_id == "env-project"
        assert config.backend_url == "http://env-host:1234"

    def test_missing_project_id_exits(self, monkeypatch):
        monkeypatch.delenv("VIDUR_PROJECT_ID", raising=False)
        with pytest.raises(SystemExit):
            local_agent.parse_args([])


# --------------------------------------------------------------------------
# Cycle assembly
# --------------------------------------------------------------------------


class TestRunCycle:
    def test_assembles_and_posts_a_full_payload(self):
        config = local_agent.AgentConfig(project_id="proj-1", backend_url="http://localhost:8000")
        counters = local_agent.ActivityCounters(clock=_FakeClock([0.0, 5.0]))
        counters.on_key_press()
        fake_psutil = _FakePsutil(cpu_values=[0.0, 15.0], disk_io_sequence=[None])
        computer_collector = local_agent.ComputerMetricsCollector(psutil_module=fake_psutil, clock=_FakeClock([100.0]))

        captured = {}

        def fake_post(payload, backend_url, project_id, timeout):
            captured["payload"] = payload
            captured["backend_url"] = backend_url
            captured["project_id"] = project_id
            return True

        result = local_agent.run_cycle(config, computer_collector, counters, post_fn=fake_post)

        assert result is True
        assert captured["project_id"] == "proj-1"
        assert captured["backend_url"] == "http://localhost:8000"
        payload = captured["payload"]
        assert set(payload.keys()) == {"personal", "computer", "environmental"}
        assert payload["personal"]["typing_speed_cpm"] == pytest.approx(12.0)
        assert payload["computer"]["cpu_usage_percent"] == 15.0
        assert payload["environmental"]["source"] in {"hardware", "simulation"}
