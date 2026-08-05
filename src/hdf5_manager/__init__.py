"""HDF5 Manager — view, edit, merge and export HDF5 files.

Built with NiceGUI for standalone use, with a framework-agnostic core
reusable in PyQt5.
"""

import sys

__version__ = "0.1.0"


def main() -> None:
    """Launch the standalone NiceGUI application.

    Entry point for:
        - Console script ``hdf5-manager`` (from pyproject.toml [project.scripts])
        - ``python -m hdf5_manager`` (implicit via this __init__.py)

    Development command — no reload to avoid the multiprocessing re-exec
    bug that occurs when ``ui.run(reload=True)`` is invoked from a
    console script wrapper. Use ``python main.py`` for hot-reload instead.
    """
    # freeze_support() MUST be the first call when running on Windows.
    # Without it, processes packaged via PyInstaller/NiceGUI-pack enter
    # an infinite-spawn loop because Windows uses 'spawn' (not 'fork')
    # for multiprocessing. On Linux/macOS this is a no-op.
    if sys.platform == "win32":
        from multiprocessing import freeze_support

        freeze_support()

    # Importing main_window triggers the @ui.page("/") decorator at
    # module level, registering the route with NiceGUI. The alias
    # ``as _`` (a throwaway name) signals we only want the side effect,
    # not any attribute access.
    # ui.run() starts the uvicorn server and opens the browser.
    # ``reload=False`` here is intentional — see docstring.
    from nicegui import ui

    import hdf5_manager.web_gui.main_window as _  # noqa: F401

    ui.run(
        title="HDF5 Manager",
        favicon="📊",
        native=False,
        reload=False,
        storage_secret="hdf5-manager-secret",
    )
