"""Input validation on the MCP tools.

The pump-range cases are regression tests for a real bug: the upstream sample
validated 0-20 for every feature, but Lovense specifies Pump as 0-3, so
out-of-range values were silently clamped to maximum by the toy.
"""

from typing import Any

import pytest
from helpers import unwrap

import RemoteMCP
import Transport

send_functions = unwrap(RemoteMCP.SendFunctions)
send_pattern = unwrap(RemoteMCP.SendPattern)
send_preset = unwrap(RemoteMCP.SendPreset)
play_script = unwrap(RemoteMCP.PlayScript)


@pytest.fixture(autouse=True)
def wired(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    """Point the tools at a stub transport so accepted input has somewhere to go."""
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(RemoteMCP, "domain_url", "https://example.invalid")

    def fake_send_functions(
        domain_url: str, toys: str, commands: str, time_sec: float
    ) -> dict[str, Any]:
        calls.append(("Function", commands))
        return {"code": 200, "type": "OK"}

    def fake_send_pattern(
        domain_url: str, toys: str, rule: str, strength: str, time_sec: float
    ) -> dict[str, Any]:
        calls.append(("Pattern", rule, strength))
        return {"code": 200, "type": "OK"}

    monkeypatch.setattr(Transport, "SendFunctions", fake_send_functions)
    monkeypatch.setattr(Transport, "SendPattern", fake_send_pattern)
    return calls


# --- SendFunctions -------------------------------------------------------


@pytest.mark.parametrize("value", [4, 7, 20])
def test_pump_above_three_is_rejected(value: int) -> None:
    result = send_functions(actions=f"Pump:{value}")
    assert result["success"] is False
    assert "0-3" in result["message"]


@pytest.mark.parametrize("value", [0, 1, 2, 3])
def test_pump_within_range_is_accepted(value: int) -> None:
    assert send_functions(actions=f"Pump:{value}")["success"] is True


def test_vibrate_above_twenty_is_rejected() -> None:
    result = send_functions(actions="Vibrate:25")
    assert result["success"] is False
    assert "0-20" in result["message"]


def test_combined_action_accepted() -> None:
    assert send_functions(actions="Vibrate:20,Pump:3")["success"] is True


def test_combined_action_rejected_on_pump() -> None:
    assert send_functions(actions="Vibrate:20,Pump:9")["success"] is False


@pytest.mark.parametrize("actions", ["Suck:2", "Vibrate", "Vibrate:abc", "Vibrate:-1"])
def test_malformed_actions_rejected(actions: str) -> None:
    assert send_functions(actions=actions)["success"] is False


def test_uninitialised_domain_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(RemoteMCP, "domain_url", "")
    assert send_functions(actions="Vibrate:5")["success"] is False


# --- SendPattern ---------------------------------------------------------


def test_pump_only_pattern_capped_at_three() -> None:
    result = send_pattern(strength="1;5;2", features="Pump")
    assert result["success"] is False
    assert "0-3" in result["message"]


def test_pump_only_pattern_accepts_zero_to_three() -> None:
    assert send_pattern(strength="0;1;2;3", features="Pump")["success"] is True


def test_combined_pattern_still_allows_full_vibration_range() -> None:
    """With v,p the list is the vibration curve; pump is derived and clamps."""
    result = send_pattern(strength="5;20", features="Vibrate,Pump")
    assert result["success"] is True
    assert "pump clamps" in result["message"]


@pytest.mark.parametrize("interval", [0, 50, 100])
def test_interval_at_or_below_spec_minimum_rejected(interval: int) -> None:
    assert send_pattern(strength="5;10", interval_ms=interval)["success"] is False


def test_interval_just_above_minimum_accepted() -> None:
    assert send_pattern(strength="5;10", interval_ms=101)["success"] is True


def test_step_limit_boundary() -> None:
    assert send_pattern(strength=";".join(["5"] * 50))["success"] is True
    assert send_pattern(strength=";".join(["5"] * 51))["success"] is False


def test_empty_strength_rejected() -> None:
    assert send_pattern(strength="")["success"] is False


def test_unknown_feature_rejected() -> None:
    assert send_pattern(strength="5", features="Suction")["success"] is False


def test_pattern_rule_is_well_formed(wired: list[tuple[str, ...]]) -> None:
    send_pattern(strength="5;10", features="Vibrate,Pump", interval_ms=500)
    assert wired[-1] == ("Pattern", "V:1;F:v,p;S:500#", "5;10")


# --- SendPreset ----------------------------------------------------------


def test_named_preset_dispatches_to_pattern(wired: list[tuple[str, ...]]) -> None:
    assert send_preset(preset="edgeplay")["success"] is True
    assert wired[-1][0] == "Pattern"


def test_unknown_preset_lists_available() -> None:
    result = send_preset(preset="tornado")
    assert result["success"] is False
    assert "edgeplay" in result["message"]


# --- PlayScript ----------------------------------------------------------


def test_unknown_script_rejected() -> None:
    result = play_script(script="nope")
    assert result["success"] is False
    assert "edgeplay" in result["message"]


@pytest.mark.parametrize("cap", [-1, 21, 99])
def test_peak_cap_out_of_range_rejected(cap: int) -> None:
    assert play_script(script="edgeplay", peak_cap=cap)["success"] is False


def test_negative_total_sec_rejected() -> None:
    assert play_script(script="edgeplay", total_sec=-5)["success"] is False
