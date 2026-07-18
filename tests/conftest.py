"""Shared test fixtures.

The autouse network block is the important one: this project drives physical
hardware, so a test that reached a real Game Mode endpoint would actuate a
device. Blocking at the socket layer means that cannot happen even if a mock is
forgotten or a code path changes underneath a test.
"""

import socket
from typing import Never

import pytest


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail loudly if any test attempts a real network connection."""

    def blocked(*args: object, **kwargs: object) -> Never:
        raise RuntimeError("Network access is blocked in tests -- a transport was left unmocked.")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
