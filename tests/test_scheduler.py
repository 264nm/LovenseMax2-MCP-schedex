"""Scheduler behaviour.

The headline claim under test is channel independence: the Pattern command
derives pump strength from the vibration values and cannot decouple them, so
the scheduler exists precisely to hold one channel steady while the other
moves. test_channels_move_independently is what justifies the module.
"""

import time
from collections.abc import Iterator
from typing import Any

import pytest
from helpers import parse, wait_idle

import Scheduler
import Transport


@pytest.fixture(autouse=True)
def recorded(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    """Record emitted commands instead of sending them, and always tidy up."""
    calls: list[str] = []

    def fake_send_functions(
        domain_url: str, toys: str, commands: str, time_sec: float
    ) -> dict[str, Any]:
        calls.append(commands)
        return {"code": 200, "type": "OK"}

    def fake_stop(domain_url: str, toys: str) -> None:
        calls.append("STOP")

    monkeypatch.setattr(Transport, "SendFunctions", fake_send_functions)
    monkeypatch.setattr(Transport, "SendStopFunction", fake_stop)
    yield calls
    Scheduler.StopScript()
    wait_idle()


def run_compressed(total_sec: float = 1.0, peak_cap: int | None = None) -> None:
    """Play edgeplay compressed into a short runtime, then wait for completion."""
    Scheduler.PlayScript(
        "https://example.invalid", "toy", "edgeplay", total_sec=total_sec, peak_cap=peak_cap
    )
    wait_idle()


def test_channels_move_independently(recorded: list[str]) -> None:
    run_compressed()
    pairs = [parse(c) for c in recorded if c != "STOP"]

    # Vibration changes while pump is held: impossible with a single Pattern.
    assert any(
        pairs[i][0] != pairs[i + 1][0] and pairs[i][1] == pairs[i + 1][1]
        for i in range(len(pairs) - 1)
    )
    # And pump genuinely varies across the run rather than tracking vibration.
    assert len({pump for _, pump in pairs}) > 1


def test_pump_led_segment_lowers_vibration_while_raising_suction(recorded: list[str]) -> None:
    """The counterpoint the design depends on: suction takes over as vibration drops."""
    run_compressed()
    pairs = [parse(c) for c in recorded if c != "STOP"]

    vibe_led = [p for p in pairs if p[1] == 1 and p[0] >= 16]
    pump_led = [p for p in pairs if p[1] == 3 and p[0] <= 14]
    assert vibe_led, "expected a vibration-led phase at pump 1"
    assert pump_led, "expected a pump-led phase at pump 3 with lower vibration"
    assert max(p[0] for p in pump_led) < max(p[0] for p in vibe_led)


def test_emitted_values_come_from_the_script(recorded: list[str]) -> None:
    run_compressed()
    pairs = [parse(c) for c in recorded if c != "STOP"]
    expected_vibe = {v for seg in Scheduler.SCRIPTS["edgeplay"]["segments"] for v in seg["vibe"]}
    expected_pump = {seg["pump"] for seg in Scheduler.SCRIPTS["edgeplay"]["segments"]}
    assert {v for v, _ in pairs} <= expected_vibe
    assert {p for _, p in pairs} <= expected_pump


def test_peak_cap_clamps_vibration(recorded: list[str]) -> None:
    run_compressed(peak_cap=16)
    vibes = [parse(c)[0] for c in recorded if c != "STOP"]
    assert max(vibes) == 16
    assert 20 not in vibes


def test_total_sec_scales_runtime() -> None:
    natural = Scheduler.ScriptDuration(Scheduler.SCRIPTS["edgeplay"])
    assert natural == 300

    started = time.monotonic()
    returned = Scheduler.PlayScript("https://example.invalid", "toy", "edgeplay", total_sec=1.0)
    wait_idle()
    elapsed = time.monotonic() - started

    assert returned == pytest.approx(1.0)
    assert elapsed < 3.0, "compressed run should not take anywhere near natural length"


def test_stop_is_sent_on_normal_completion(recorded: list[str]) -> None:
    run_compressed()
    assert recorded[-1] == "STOP"


def test_cancellation_halts_further_commands(recorded: list[str]) -> None:
    Scheduler.PlayScript("https://example.invalid", "toy", "edgeplay", total_sec=20.0)
    time.sleep(0.5)
    assert Scheduler.StopScript() == "edgeplay"
    wait_idle()

    settled = len(recorded)
    time.sleep(0.3)
    assert len(recorded) == settled, "commands continued after cancellation"
    assert "STOP" in recorded


def test_stop_is_sent_even_when_transport_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failure mid-run must never leave the toy running."""
    stopped: list[str] = []

    def exploding_send(
        domain_url: str, toys: str, commands: str, time_sec: float
    ) -> dict[str, Any]:
        raise RuntimeError("transport died")

    monkeypatch.setattr(Transport, "SendFunctions", exploding_send)
    monkeypatch.setattr(
        Transport, "SendStopFunction", lambda domain_url, toys: stopped.append("STOP")
    )

    Scheduler.PlayScript("https://example.invalid", "toy", "edgeplay", total_sec=1.0)
    wait_idle()
    assert stopped == ["STOP"]


def test_second_concurrent_script_is_refused() -> None:
    Scheduler.PlayScript("https://example.invalid", "toy", "edgeplay", total_sec=5.0)
    with pytest.raises(ValueError, match="already running"):
        Scheduler.PlayScript("https://example.invalid", "toy", "edgeplay")


def test_unknown_script_raises() -> None:
    with pytest.raises(ValueError, match="Unknown script"):
        Scheduler.PlayScript("https://example.invalid", "toy", "nope")


def test_stop_script_returns_none_when_idle() -> None:
    assert Scheduler.StopScript() is None


def test_get_script_is_case_insensitive() -> None:
    assert Scheduler.GetScript("EdgePlay") is Scheduler.GetScript("edgeplay")
    assert Scheduler.GetScript("nope") is None
