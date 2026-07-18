# Transport.py
# HTTP client for the Lovense Game Mode local API.
#
# Independent implementation written against the publicly documented protocol
# at developer.lovense.com. No upstream sample code is used or included, so
# this file carries no third-party licensing encumbrance.
#
# Deliberate differences from the vendor sample this replaced:
#   - Logs through the logging module rather than print(). This server speaks
#     MCP over stdio, where stdout is the protocol channel, so writing
#     diagnostics there risks corrupting the stream.
#   - Every request has a timeout. Without one a stalled connection blocks the
#     caller indefinitely, which for a scheduled script means a hung thread.
#   - One shared _post helper instead of the same request boilerplate per
#     command.

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Game Mode is a device on the local network; it either answers promptly or is
# gone (app backgrounded, screen locked, phone off wifi).
DEFAULT_TIMEOUT = 10.0


def _post(
    domain_url: str, payload: dict[str, Any], timeout: float = DEFAULT_TIMEOUT
) -> dict[str, Any] | None:
    """
    POST a command to the Game Mode endpoint.

    Returns the decoded response body, or None if the endpoint returned a
    non-200 status.
    """
    command = payload.get("command", "?")
    response = requests.post(f"{domain_url}/command", json=payload, timeout=timeout)
    if response.status_code != 200:
        logger.error("%s failed with HTTP %s", command, response.status_code)
        return None
    body: dict[str, Any] = response.json()
    logger.debug("%s -> %s", command, body)
    return body


def GetToys(domain_url: str) -> dict[str, Any] | None:
    """List connected toys with their IDs, names, functions, battery and status."""
    return _post(domain_url, {"command": "GetToys", "apiVer": 1})


def SendFunctions(
    domain_url: str, toys: str, commands: str, time_sec: float
) -> dict[str, Any] | None:
    """
    Run one or more functions, e.g. "Vibrate:10" or "Vibrate:10,Pump:2".

    Vibrate and Rotate accept 0-20, Pump only 0-3. time_sec of 0 runs until
    stopped. An empty toys targets every connected toy.
    """
    return _post(
        domain_url,
        {
            "command": "Function",
            "action": commands,
            "timeSec": time_sec,
            "toy": toys,
            "apiVer": 1,
        },
    )


def SendPreset(
    domain_url: str, toys: str, preset_name: str, time_sec: float
) -> dict[str, Any] | None:
    """Run a built-in preset pattern: pulse, wave, fireworks or earthquake."""
    return _post(
        domain_url,
        {
            "command": "Preset",
            "name": preset_name,
            "timeSec": time_sec,
            "toy": toys,
            "apiVer": 1,
        },
    )


def SendPattern(
    domain_url: str, toys: str, rule: str, strength: str, time_sec: float
) -> dict[str, Any] | None:
    """
    Play a custom pattern, e.g. rule "V:1;F:v;S:500#" with strength
    "5;10;15;20;10". The strength sequence loops until time_sec elapses.

    Requires apiVer 2, unlike the other commands. Pump and rotation strength
    are derived from the vibration values, so a pattern cannot drive them on an
    independent curve; Scheduler.py exists for that case.
    """
    return _post(
        domain_url,
        {
            "command": "Pattern",
            "rule": rule,
            "strength": strength,
            "timeSec": time_sec,
            "toy": toys,
            "apiVer": 2,
        },
    )


def SendStopFunction(domain_url: str, toys: str) -> dict[str, Any] | None:
    """Immediately stop all running actions."""
    return _post(
        domain_url,
        {
            "command": "Function",
            "action": "Stop",
            "timeSec": 0,
            "toy": toys,
            "apiVer": 1,
        },
    )
