"""Game Mode wire format.

Payload shapes are asserted against the publicly documented protocol. The
apiVer split matters: Pattern requires apiVer 2 while every other command uses
apiVer 1.
"""

from collections.abc import Callable
from typing import Any

import pytest
import requests

import Transport


class FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return {"code": 200, "type": "OK"}


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    box: dict[str, Any] = {}

    def fake_post(url: str, *, json: dict[str, Any], timeout: float) -> FakeResponse:
        box["url"] = url
        box["json"] = json
        box["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    return box


HOST = "https://host:30010"


# --- shared request behaviour --------------------------------------------


def test_posts_to_command_endpoint(captured: dict[str, Any]) -> None:
    Transport.GetToys(HOST)
    assert captured["url"] == f"{HOST}/command"


def test_every_request_has_a_timeout(captured: dict[str, Any]) -> None:
    """Without a timeout a stalled connection blocks a scheduler thread forever."""
    Transport.GetToys(HOST)
    assert captured["timeout"] == Transport.DEFAULT_TIMEOUT


def test_non_200_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        requests, "post", lambda url, *, json, timeout: FakeResponse(status_code=500)
    )
    assert Transport.GetToys(HOST) is None


def test_success_returns_decoded_body(captured: dict[str, Any]) -> None:
    assert Transport.GetToys(HOST) == {"code": 200, "type": "OK"}


# --- per-command payloads ------------------------------------------------


def test_get_toys_payload(captured: dict[str, Any]) -> None:
    Transport.GetToys(HOST)
    assert captured["json"] == {"command": "GetToys", "apiVer": 1}


def test_send_functions_payload(captured: dict[str, Any]) -> None:
    Transport.SendFunctions(HOST, "toy1", "Vibrate:10,Pump:2", 5)
    assert captured["json"] == {
        "command": "Function",
        "action": "Vibrate:10,Pump:2",
        "timeSec": 5,
        "toy": "toy1",
        "apiVer": 1,
    }


def test_send_preset_payload(captured: dict[str, Any]) -> None:
    Transport.SendPreset(HOST, "toy1", "pulse", 10)
    assert captured["json"] == {
        "command": "Preset",
        "name": "pulse",
        "timeSec": 10,
        "toy": "toy1",
        "apiVer": 1,
    }


def test_send_pattern_payload_uses_api_version_two(captured: dict[str, Any]) -> None:
    Transport.SendPattern(HOST, "toy1", "V:1;F:v,p;S:6000#", "1;20", 300)
    assert captured["json"] == {
        "command": "Pattern",
        "rule": "V:1;F:v,p;S:6000#",
        "strength": "1;20",
        "timeSec": 300,
        "toy": "toy1",
        "apiVer": 2,
    }


def test_stop_payload(captured: dict[str, Any]) -> None:
    Transport.SendStopFunction(HOST, "")
    assert captured["json"] == {
        "command": "Function",
        "action": "Stop",
        "timeSec": 0,
        "toy": "",
        "apiVer": 1,
    }


@pytest.mark.parametrize(
    "call",
    [
        lambda: Transport.GetToys(HOST),
        lambda: Transport.SendFunctions(HOST, "t", "Vibrate:1", 1),
        lambda: Transport.SendPreset(HOST, "t", "pulse", 1),
        lambda: Transport.SendStopFunction(HOST, "t"),
    ],
)
def test_non_pattern_commands_use_api_version_one(
    captured: dict[str, Any], call: Callable[[], dict[str, Any] | None]
) -> None:
    call()
    assert captured["json"]["apiVer"] == 1
