"""
Shared pytest fixtures.

These tests run without a real Anki installation: the modules under test only
need the ``aqt`` package to exist (they import ``mw`` from it).  We provide a
minimal stand-in so that ``src.get_diff`` can be imported, plus lightweight
mocks of the collection objects used by ``calculate_notes_difficulties``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


class _FakeAqt(types.ModuleType):
    mw = None  # type: ignore[assignment]


def _install_aqt_stub() -> None:
    if "aqt" not in sys.modules:
        stub = _FakeAqt("aqt")
        stub.mw = None
        sys.modules["aqt"] = stub
    # always point the stub's mw at the most recent fake mw
    sys.modules["aqt"].mw = getattr(sys.modules["aqt"], "mw", None)  # type: ignore[union-attr]


_install_aqt_stub()

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture()
def fake_mw():
    """Return a mock ``mw`` whose collection is backed by in-memory objects."""
    from tests.fake_collection import FakeCollection, FakeMw

    import src.get_diff as get_diff

    aqt = sys.modules["aqt"]
    old_mw = aqt.mw
    old_get_diff_mw = get_diff.mw
    mw = FakeMw()
    aqt.mw = mw
    get_diff.mw = mw
    yield mw
    aqt.mw = old_mw
    get_diff.mw = old_get_diff_mw
