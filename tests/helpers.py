"""Test helpers."""

import time
from collections.abc import Callable
from typing import Any, cast

import Scheduler

# Per-feature strength ceilings from the Lovense spec: Vibrate and Rotate accept
# 0-20, Pump only 0-3.
FEATURE_CEILINGS = {"v": 20, "r": 20, "p": 3}


def unwrap(tool: object) -> Callable[..., dict[str, Any]]:
    """Get the underlying function from a FastMCP tool object.

    Depending on the mcp version, @mcp.tool() either returns the function
    unchanged or wraps it in a FunctionTool exposing it as .fn.
    """
    return cast("Callable[..., dict[str, Any]]", getattr(tool, "fn", tool))


def wait_idle(timeout: float = 10.0) -> None:
    """Block until the scheduler has no running script."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        thread = Scheduler._active["thread"]
        if thread is None or not thread.is_alive():
            return
        time.sleep(0.01)
    raise AssertionError("scheduler did not finish within timeout")


def parse(command: str) -> tuple[int, int]:
    """Split a 'Vibrate:N,Pump:M' command into (vibe, pump)."""
    vibe, _, pump = command.partition(",")
    return int(vibe.split(":")[1]), int(pump.split(":")[1])
