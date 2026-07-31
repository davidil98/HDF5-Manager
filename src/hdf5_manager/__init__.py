"""HDF5 Manager — view, edit, merge and export HDF5 files.

Built with NiceGUI for standalone use, with a framework-agnostic core
reusable in PyQt5.
"""

__version__ = "0.1.0"


def main() -> None:
    """Launch the standalone NiceGUI application."""
    from hdf5_manager.web_gui import main_window

    main_window.run()
