"""Pattern preset data integrity.

These assert the Lovense Pattern spec limits (max 50 steps, per-feature strength
ceilings) and the duration arithmetic each preset's design depends on.
"""

import pytest
from helpers import FEATURE_CEILINGS

import Patterns


def steps_of(name: str) -> list[int]:
    return [int(s) for s in Patterns.PATTERNS[name]["strength"].split(";") if s.strip()]


@pytest.mark.parametrize("name", sorted(Patterns.PATTERNS))
def test_within_step_limit(name: str) -> None:
    assert len(steps_of(name)) <= 50, "Lovense caps a pattern at 50 strength values"


@pytest.mark.parametrize("name", sorted(Patterns.PATTERNS))
def test_strength_within_feature_ceiling(name: str) -> None:
    features = Patterns.PATTERNS[name]["features"].split(",")
    # A pattern listing v,p carries the *vibration* curve, with pump derived
    # from it, so the ceiling is the highest of the listed features.
    ceiling = max(FEATURE_CEILINGS[f] for f in features)
    assert all(0 <= value <= ceiling for value in steps_of(name))


@pytest.mark.parametrize("name", sorted(Patterns.PATTERNS))
def test_interval_above_spec_minimum(name: str) -> None:
    assert Patterns.PATTERNS[name]["interval_ms"] > 100


def test_edgeplay_cycle_is_exactly_five_minutes() -> None:
    """edgeplay is a one-shot macro arc, so its cycle must fill time_sec exactly."""
    preset = Patterns.PATTERNS["edgeplay"]
    cycle_sec = len(steps_of("edgeplay")) * preset["interval_ms"] / 1000
    assert cycle_sec == 300.0
    assert preset["time_sec"] == 300


def test_motif_fits_in_app_editor_timeline() -> None:
    """The Lovense in-app pattern editor works on a 10-30s timeline."""
    preset = Patterns.PATTERNS["edgeplay_motif"]
    cycle_sec = len(steps_of("edgeplay_motif")) * preset["interval_ms"] / 1000
    assert 10 <= cycle_sec <= 30


def test_get_pattern_builds_rule() -> None:
    result = Patterns.GetPattern("edgeplay")
    assert result is not None
    rule, strength, time_sec = result
    assert rule == "V:1;F:v,p;S:6000#"
    assert strength == Patterns.PATTERNS["edgeplay"]["strength"]
    assert time_sec == 300


def test_get_pattern_is_case_insensitive() -> None:
    assert Patterns.GetPattern("EdgePlay") == Patterns.GetPattern("edgeplay")


def test_get_pattern_unknown_returns_none() -> None:
    assert Patterns.GetPattern("nonexistent") is None
