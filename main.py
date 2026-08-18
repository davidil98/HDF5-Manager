"""HDF5 Manager development entry point.

Usage:
    python main.py          # Development profile with reload enabled

Edit ``DEV_NATIVE`` to develop in a native window. Distribution uses the
separate production profile from ``hdf5_manager.launcher``.
"""

import sys


# Native mode needs freeze_support on Windows when packaged.
# Debe ser la PRIMERA llamada en el proceso principal.
if sys.platform == "win32":
    from multiprocessing import freeze_support

    freeze_support()
    
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from hdf5_manager.launcher import run_development

DEV_NATIVE = True
DEV_RELOAD = True

if __name__ in {"__main__", "__mp_main__"}:
    run_development(native=DEV_NATIVE, reload=DEV_RELOAD)
