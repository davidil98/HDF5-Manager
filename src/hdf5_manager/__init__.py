"""HDF5 Manager — view, edit, merge and export HDF5 files.

Built with NiceGUI for standalone use, with a framework-agnostic core
reusable in PyQt5.
"""

__version__ = "0.1.0"


def main() -> None:
    """Launch the reload-free production profile.

    Entry point for:
        - Console script ``hdf5-manager`` (from pyproject.toml [project.scripts])
        - ``python -m hdf5_manager``
        - ``hdf5-manager`` from the console script

    Native mode is attempted by default and falls back to the local web
    browser when its preflight checks fail.
    """
    # freeze_support() MUST be the first call when running on Windows.
    # Without it, processes packaged via PyInstaller/NiceGUI-pack enter
    # an infinite-spawn loop because Windows uses 'spawn' (not 'fork')
    # for multiprocessing. On Linux/macOS this is a no-op.
    import sys

    if sys.platform == "win32":
        from multiprocessing import freeze_support

        freeze_support()

    from hdf5_manager.launcher import main as run_production

    run_production()
