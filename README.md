# HDF5 Manager

A standalone desktop tool for viewing, editing, merging, and exporting
[HDF5](https://www.hdfgroup.org/solutions/hdf5/) files. Built with
[NiceGUI](https://nicegui.io/), with a framework-agnostic core reusable in PyQt5.

## Features

- **View** — Browse the HDF5 tree structure, inspect attributes, preview
  dataset contents
- **Edit** — Rename groups and datasets, delete nodes
- **Merge** — Copy groups between files, combine measurement runs
- **Export** — Convert datasets to CSV or Excel in three layouts:
  - **Datasets side by side** — one named file with all selected datasets as
    columns
  - **One sheet per group** — one named Excel workbook with one sheet for
    each selected group
  - **One file per group** — one automatically named CSV or Excel file per
    selected group

## Installation

### From source (development)

```bash
git clone https://github.com/davidil98/HDF5-Manager.git
cd HDF5-Manager
pip install -e ".[dev]"
```

### conda

```bash
conda env create -f environment.yml
conda activate hdf5_manager
```

### From PyPI (when published)

```bash
pip install hdf5-manager
```

## Usage

### Development

```bash
python main.py        # Hot-reload, browser mode
hdf5-manager          # No reload, browser mode (from console script)
```

Both commands work in browser mode (default for development).
`python main.py` enables hot-reload — saving any `.py` reloads the page.

### End-user distribution

Windows users with conda, double-click `run.bat` or from Anaconda Prompt:

```batch
conda activate hdf5_manager
hdf5-manager
```

Linux/macOS users with conda:

```bash
./run.sh
```

For native mode (desktop window instead of browser), install the GUI
extras first:

```bash
pip install -e ".[gui]"      # pip users
# or, already covered by environment.yml for conda users (pywebview[qt])
```

Then launch with native mode (edit `__init__.py` to set `native=True`
or pass it explicitly).

Or build a standalone `.exe` for distribution:

```bash
nicegui-pack --onefile --name "HDF5-Manager" main.py
```

> **Linux note:** native mode is **fully working on Fedora** (tested
> with PyQt6-WebEngine). Ubuntu/Debian users may have a smoother
> experience because `apt` provides `libwebkit2gtk` and `python3-gi`
> packages out of the box, so the GTK backend of pywebview is usable
> without extra steps. On Fedora, pywebview falls through to Qt6
> because the system ships Gtk 4 only. See `AGENTS.md` for details.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
ruff format src/ tests/   # optional auto-formatting
mypy src/
```

## Architecture

```
hdf5_manager/
├── core/          # Pure h5py + pandas logic, zero GUI dependencies
├── web_gui/       # NiceGUI standalone frontend
└── pyqt_gui/      # Future PyQt5 widget for nanomol integration
```

`core/` is framework-agnostic and testable with pytest. Both frontends import
from core, never the reverse.

### Entry points

| Command              | File                        | reload | native |
|----------------------|-----------------------------|--------|--------|
| `python main.py`     | `main.py`                   | True   | False  |
| `hdf5-manager`       | `src/hdf5_manager/__init__.py` | False  | False  |
| `run.bat` / `run.sh` | (user scripts)              | False  | True   |

## Distribution

- **PyPI** — `pip install hdf5-manager`
- **conda** — `conda env create -f environment.yml`
- **Windows .exe** — `nicegui-pack --onefile --name "HDF5-Manager" main.py`
- **GitHub Releases** — Pre-built .exe attached to each release

## License

MIT — see [LICENSE](LICENSE).
