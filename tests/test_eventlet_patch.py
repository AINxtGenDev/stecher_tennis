"""Smoke test for WR-03: eventlet monkey-patching is applied correctly.

Importing the app (done in conftest) runs eventlet.monkey_patch() at the very
top of app.py. These tests confirm the patch took effect and that logging still
works afterwards (i.e. no eventlet/logging lock deadlock from bad import order).
"""
import logging

import eventlet


def test_stdlib_is_monkey_patched():
    assert eventlet.patcher.is_monkey_patched("socket")
    assert eventlet.patcher.is_monkey_patched("thread")
    assert eventlet.patcher.is_monkey_patched("time")


def test_logging_works_after_patch():
    # Would hang on an eventlet/logging lock deadlock; completing is the assertion.
    logging.getLogger("wr03_smoke").info("eventlet monkey-patch smoke log")
