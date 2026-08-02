"""
VIDUR Core - Specs
Submodule: Enums
Purpose: Shared enumerations for the Specs module.
"""

from enum import Enum


class MetricStatus(str, Enum):
    """Whether a single Specs metric reading was actually supplied.

    Every metric in every category (Personal, Computer, Environmental)
    is reported through this status - a metric the caller did not
    supply is PRESENT: False / MISSING, never fabricated or silently
    defaulted (CLAUDE.md Specs Module: Missing-sensor handling).
    """

    PRESENT = "present"
    MISSING = "missing"


class EnvironmentalSource(str, Enum):
    """How an Environmental metrics reading was obtained, per
    CLAUDE.md's simulation-with-automatic-hardware-handoff contract:
    the local agent scans for a known Arduino/ESP32 USB vendor:product
    ID every cycle and reports which path produced the reading."""

    HARDWARE = "hardware"
    SIMULATION = "simulation"


class ConfidenceLevel(str, Enum):
    """How much historical evidence backs a Specs ML Prediction Engine
    output. Never inflated - CLAUDE.md's Cold start rule requires the
    upcoming-session prediction to "clearly mark low/no confidence" and
    never claim a trained model produced a number when nothing has
    trained yet."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
