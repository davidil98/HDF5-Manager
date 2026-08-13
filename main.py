"""HDF5 Manager — standalone desktop application.

Usage:
    python main.py          # End-user / packaged .exe entry point
    hdf5-manager            # Dev entry (console script, same behaviour)

Note: native=False opens the app in the system browser (Edge/Chrome on
Windows). No pywebview dependency required. Set native=True only after
installing the [gui] extras (pywebview[qt]).
"""
import sys
# Native mode needs freeze_support on Windows when packaged.
# Debe ser la PRIMERA llamada en el proceso principal.
if sys.platform == "win32":
    from multiprocessing import freeze_support

    freeze_support()
    
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from nicegui import ui

import hdf5_manager.web_gui.main_window as _ 

if __name__ in {"__main__", "__mp_main__"}:
    
    ui.run(
        title="HDF5 Manager",
        favicon="📊",
        native=False,   # browser mode — no pywebview needed; works on all OS
        reload=False,   # must be False in packaged .exe and console scripts
        storage_secret="hdf5-manager-secret",
    )
