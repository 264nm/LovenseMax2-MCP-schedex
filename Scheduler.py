# Scheduler.py
# Timed multi-channel scripts: drives Vibrate and Pump on independent curves.
#
# The Pattern command derives pump strength from the vibration values, so it
# cannot make the two channels counterpoint each other. This scheduler issues
# timed Function commands instead, setting both channels explicitly on every
# step. The trade-off is that it needs the phone connection to stay alive for
# the whole run, whereas a Pattern is uploaded once and executes on the phone.
# Patterns.py carries a single-curve "edgeplay" fallback for that case.

import logging
import threading
from typing import TypedDict

import Transport

logger = logging.getLogger(__name__)


class Segment(TypedDict):
    """One phase of a script: a vibration cycle held against a fixed pump level."""

    name: str
    duration: float
    step: float
    vibe: list[int]
    pump: int


class ScriptSpec(TypedDict):
    """A named multi-channel script."""

    description: str
    segments: list[Segment]


class _ActiveScript(TypedDict):
    """The currently running script, if any. Guarded by _lock."""

    thread: threading.Thread | None
    stop: threading.Event | None
    name: str | None


# Each segment holds a vibration cycle plus a single pump level. Pump is set
# once per segment because the Max's air pump actuates far more slowly than the
# vibration motor and will not track fast level changes.
#
# "edgeplay" is threshold-biased rather than texture-biased: sustained amplitude
# is the lever that crosses threshold (Sonksen et al. 1994,
# doi:10.1038/sc.1994.105), so it holds three 75s plateaus with rising absolute
# intensity. The 10s swaps exist to change which receptor population carries the
# load -- vibration is rapidly-adapting, suction slowly-adapting, and the two
# adapt independently (Hollins et al. 1990, doi:10.3109/08990229009144707).
SCRIPTS: dict[str, ScriptSpec] = {
    "edgeplay": {
        "description": (
            "5-minute edging plateau, threshold-biased, vibration and suction alternating"
        ),
        "segments": [
            {"name": "warm-up", "duration": 30, "step": 3.0, "vibe": [8, 9, 10, 11, 12], "pump": 1},
            {"name": "vibe-led", "duration": 75, "step": 5.0, "vibe": [16, 17, 18, 17], "pump": 1},
            {"name": "swap", "duration": 10, "step": 10.0, "vibe": [4], "pump": 0},
            {"name": "pump-led", "duration": 75, "step": 5.0, "vibe": [12, 13, 14, 13], "pump": 3},
            {"name": "swap", "duration": 10, "step": 10.0, "vibe": [4], "pump": 0},
            {"name": "both", "duration": 75, "step": 5.0, "vibe": [18, 19, 20, 19], "pump": 3},
            {"name": "plateau", "duration": 25, "step": 25.0, "vibe": [14], "pump": 1},
        ],
    },
}

_lock = threading.Lock()
_active: _ActiveScript = {"thread": None, "stop": None, "name": None}


def GetScript(name: str) -> ScriptSpec | None:
    """Look up a named script, or None if unknown."""
    return SCRIPTS.get(name.lower())


def ScriptDuration(script: ScriptSpec) -> float:
    """Natural (unscaled) runtime of a script in seconds."""
    return sum(segment["duration"] for segment in script["segments"])


def _run(
    domain_url: str,
    toy: str,
    script: ScriptSpec,
    scale: float,
    peak_cap: int | None,
    stop_event: threading.Event,
) -> None:
    try:
        for segment in script["segments"]:
            duration = segment["duration"] * scale
            step = min(segment["step"] * scale, duration)
            pump = segment["pump"]
            elapsed = 0.0
            index = 0
            while elapsed < duration - 1e-9:
                if stop_event.is_set():
                    return
                vibe = segment["vibe"][index % len(segment["vibe"])]
                if peak_cap is not None:
                    vibe = min(vibe, peak_cap)
                hold = min(step, duration - elapsed)
                # timeSec deliberately outruns the step so the channels do not
                # drop out between commands; the next command overwrites it.
                Transport.SendFunctions(
                    domain_url, toy, f"Vibrate:{vibe},Pump:{pump}", round(hold + 1, 2)
                )
                if stop_event.wait(hold):
                    return
                elapsed += hold
                index += 1
    except Exception:
        # A transport failure mid-run (typically the phone dropping the Game
        # Mode connection) aborts the script rather than spamming a dead
        # endpoint. Logged rather than raised: this runs on a worker thread, so
        # an escaping exception would be invisible to the caller and would kill
        # the thread with an unhandled traceback instead of stopping cleanly.
        logger.exception("Scheduler aborted mid-script")
    finally:
        # Runs on normal completion, cancellation and failure alike, so nothing
        # ever leaves the toy running.
        try:
            Transport.SendStopFunction(domain_url, toy)
        except Exception:
            logger.exception("Scheduler stop-on-exit failed")
        with _lock:
            if _active["stop"] is stop_event:
                _active["thread"] = None
                _active["stop"] = None
                _active["name"] = None


def PlayScript(
    domain_url: str,
    toy: str,
    name: str,
    total_sec: float | None = None,
    peak_cap: int | None = None,
) -> float:
    """
    Start a script on a background thread and return its runtime in seconds.

    Args:
        total_sec: Compress or stretch the whole script to this runtime,
            preserving segment proportions. None runs it at natural length.
        peak_cap: Clamp every vibration value to at most this, for calibration
            runs. None runs the script's own values.

    Raises ValueError for an unknown name or if a script is already running.
    """
    script = GetScript(name)
    if not script:
        raise ValueError(f"Unknown script: {name} (available: {', '.join(SCRIPTS)})")

    with _lock:
        thread = _active["thread"]
        if thread is not None and thread.is_alive():
            raise ValueError(f"Script '{_active['name']}' is already running -- stop it first")

        natural = ScriptDuration(script)
        scale = (total_sec / natural) if total_sec else 1.0
        stop_event = threading.Event()
        worker = threading.Thread(
            target=_run,
            args=(domain_url, toy, script, scale, peak_cap, stop_event),
            daemon=True,
        )
        _active["thread"] = worker
        _active["stop"] = stop_event
        _active["name"] = name.lower()
        worker.start()

    return natural * scale


def StopScript() -> str | None:
    """Signal any running script to stop. Returns the script name, or None."""
    with _lock:
        stop_event = _active["stop"]
        name = _active["name"]
    if stop_event:
        stop_event.set()
    return name
