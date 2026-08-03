"""HDF5 Manager — standalone desktop application.

Usage:
    python main.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from hdf5_manager import main

if __name__ == "__main__":
    main()
