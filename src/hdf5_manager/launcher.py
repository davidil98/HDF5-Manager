"""Application launch profiles shared by development and distribution."""

from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import sys
from typing import Literal

Mode = Literal["auto", "native", "web"]

_LOGGER = logging.getLogger(__name__)


def native_preflight() -> tuple[bool, str]:
    """Return whether the current process can reasonably start native mode."""
    if importlib.util.find_spec("webview") is None:
        return False, "pywebview is not installed"
    if sys.platform.startswith("linux") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        return False, "no Linux graphical display was detected"
    return True, "native dependencies and display detected"


def resolve_native(mode: Mode) -> bool:
    """Resolve the requested deployment mode to a native flag."""
    if mode == "web":
        return False
    available, reason = native_preflight()
    if mode == "native":
        if not available:
            raise RuntimeError(f"Native mode is unavailable: {reason}")
        return True
    if available:
        _LOGGER.info("Starting native mode: %s", reason)
        return True
    _LOGGER.warning("Native mode unavailable; falling back to web mode: %s", reason)
    return False


def _register_application() -> None:
    """Import the page module so NiceGUI registers its routes."""
    import hdf5_manager.web_gui.main_window as _  # noqa: F401


def run_application(*, native: bool, reload: bool) -> None:
    """Run NiceGUI with an already resolved profile."""
    from nicegui import ui

    _register_application()
    ui.run(
        title="HDF5 Manager",
        favicon="📊",
        native=native,
        window_size=(1280, 800) if native else None,
        host="127.0.0.1" if not native else None,
        reload=reload,
        storage_secret="hdf5-manager-secret",
    )


def run_development(*, native: bool = False, reload: bool = True) -> None:
    """Run the independently configurable development profile."""
    run_application(native=native, reload=reload)


def run_production(mode: Mode = "auto") -> None:
    """Run the reload-free profile used by the console script and EXE."""
    native = resolve_native(mode)
    try:
        run_application(native=native, reload=False)
    except SystemExit:
        # NiceGUI exits early when native optional features are unavailable.
        # In auto mode the web server is still a valid recovery path.
        if mode != "auto" or not native:
            raise
        _LOGGER.exception("Native startup failed; falling back to web mode")
        run_application(native=False, reload=False)


def main(argv: list[str] | None = None) -> None:
    """Parse production options and start the application."""
    parser = argparse.ArgumentParser(description="Run HDF5 Manager")
    parser.add_argument(
        "--mode",
        choices=("auto", "native", "web"),
        default=os.environ.get("HDF5_MANAGER_MODE", "auto"),
        help="deployment mode (default: auto)",
    )
    args, _ = parser.parse_known_args(argv)
    run_production(args.mode)
