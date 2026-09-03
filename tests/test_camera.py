"""Regression tests for resilient camera opening and reconnect behavior."""
from __future__ import annotations

from collections import deque

import numpy as np

from src.core.camera import ResilientCamera


class FakeCapture:
    def __init__(self, *, opened=True, reads=()) -> None:
        self.opened = opened
        self.reads = deque(reads)
        self.released = False
        self.properties = {}

    def isOpened(self):
        return self.opened and not self.released

    def read(self):
        if self.reads:
            return self.reads.popleft()
        return False, None

    def set(self, prop_id, value):
        self.properties[prop_id] = value
        return True

    def get(self, prop_id):
        return self.properties.get(prop_id, 0.0)

    def release(self):
        self.released = True


def test_camera_falls_back_to_next_backend():
    captures = [FakeCapture(opened=False), FakeCapture(opened=True)]
    calls = []

    def factory(source, backend=None):
        calls.append((source, backend))
        return captures.pop(0)

    camera = ResilientCamera(
        2,
        backends=(101, 202),
        capture_factory=factory,
        reconnect_cooldown=0,
    )

    assert camera.open()
    assert camera.isOpened()
    assert calls == [(2, 101), (2, 202)]
    assert camera.open_attempts == 2


def test_camera_reconnects_after_repeated_failed_reads():
    frame = np.ones((8, 8, 3), dtype=np.uint8)
    captures = [
        FakeCapture(reads=[(False, None), (False, None)]),
        FakeCapture(reads=[(True, frame)]),
    ]

    def factory(_source, _backend=None):
        return captures.pop(0)

    camera = ResilientCamera(
        0,
        backends=(101,),
        max_consecutive_failures=2,
        reconnect_cooldown=0,
        capture_factory=factory,
    )
    assert camera.open()

    assert camera.read() == (False, None)
    assert camera.read() == (False, None)
    ok, recovered = camera.read()

    assert ok
    assert np.array_equal(recovered, frame)
    assert camera.reconnects == 1
    assert camera.read_failures == 2


def test_camera_property_proxy_and_release():
    capture = FakeCapture(opened=True)
    camera = ResilientCamera(
        0,
        backends=(101,),
        capture_factory=lambda *_args: capture,
        reconnect_cooldown=0,
    )
    assert camera.open()
    assert camera.set(3, 640)
    assert camera.get(3) == 640.0

    camera.release()
    assert not camera.isOpened()
    assert capture.released
