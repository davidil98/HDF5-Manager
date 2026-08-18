"""Production entry point used to build the standalone executable."""

import sys


if sys.platform == "win32":
    from multiprocessing import freeze_support

    freeze_support()

from hdf5_manager import main


if __name__ in {"__main__", "__mp_main__"}:
    main()
