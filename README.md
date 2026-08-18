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
python main.py                    # Development profile, reload enabled
hdf5-manager --mode web           # Production profile, browser mode
hdf5-manager --mode native        # Require native mode
hdf5-manager --mode auto          # Native first, web fallback
```

`python main.py` is intentionally independent from the distribution profile.
Its `DEV_NATIVE` and `DEV_RELOAD` constants can be changed when developing.
The `hdf5-manager` console script always uses `reload=False`.

### End-user distribution

Windows users with conda can double-click `run.bat` or run it from Anaconda
Prompt:

```batch
conda activate hdf5_manager
hdf5-manager
```

The production launcher tries to open a native pywebview window first. If the
native preflight fails, it falls back to the local web browser. Use
`hdf5-manager --mode web` to force browser mode or `--mode native` to require
the native window.

Linux/macOS users with conda can use:

```bash
./run.sh
```

The `run.sh` launcher uses the same native-first production profile.

Or build a standalone `.exe` for distribution:

```bash
nicegui-pack --onefile --name "HDF5-Manager" packaged_main.py
```

The executable uses the same production launcher as `hdf5-manager` and always
uses `reload=False`.

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
| `python main.py`     | `main.py`                   | True   | Configurable |
| `hdf5-manager`       | `src/hdf5_manager/__init__.py` | False  | Auto |
| `.exe`               | `packaged_main.py`          | False  | Auto |
| `run.bat` / `run.sh` | (production launchers)      | False  | Auto |

## Distribution

- **PyPI** — `pip install hdf5-manager`
- **conda** — `conda env create -f environment.yml`
- **Windows .exe** — `nicegui-pack --onefile --name "HDF5-Manager" main.py`
- **GitHub Releases** — Pre-built .exe attached to each release

## License

MIT — see [LICENSE](LICENSE).
