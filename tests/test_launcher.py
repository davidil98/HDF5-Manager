"""Tests for deployment mode selection."""

from __future__ import annotations

import pytest

from hdf5_manager import launcher


def test_web_mode_never_requires_native_dependencies() -> None:
    """Explicit web mode should always resolve to browser execution."""
    assert launcher.resolve_native("web") is False


def test_auto_mode_falls_back_when_pywebview_is_missing(monkeypatch) -> None:
    """Auto mode should select web when native dependencies are unavailable."""
    monkeypatch.setattr(launcher.importlib.util, "find_spec", lambda _name: None)
    assert launcher.resolve_native("auto") is False


def test_native_mode_reports_missing_dependencies(monkeypatch) -> None:
    """Explicit native mode should fail clearly instead of silently falling back."""
    monkeypatch.setattr(launcher.importlib.util, "find_spec", lambda _name: None)
    with pytest.raises(RuntimeError, match="pywebview is not installed"):
        launcher.resolve_native("native")
