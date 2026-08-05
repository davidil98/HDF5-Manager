"""HDF5 Manager — standalone desktop application.

Usage:
    python main.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from nicegui import ui

import hdf5_manager.web_gui.main_window as _ 

if __name__ in {"__main__", "__mp_main__"}:
    # Native mode needs freeze_support on Windows when packaged.
    # Debe ser la PRIMERA llamada en el proceso principal.
    if sys.platform == "win32":
        from multiprocessing import freeze_support

        freeze_support()
    
    ui.run(
        title="HDF5 Manager",
        favicon="📊",
        native=True,
        #window_size=(1200, 800),
        reload=True,
        storage_secret="hdf5-manager-secret",
    )
