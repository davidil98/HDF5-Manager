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
  - Side-by-side tables
  - One sheet per group (Excel)
  - One file per group

## Installation

### pip (PyPI)

```bash
pip install hdf5-manager
```

### conda

```bash
conda env create -f environment.yml
conda activate hdf5_manager
```

## Usage

### Standalone desktop app

```bash
hdf5-manager
```

Or run directly:

```bash
python main.py
```

### Windows users with conda

Double-click `run.bat`, or from Anaconda Prompt:

```bash
conda activate hdf5_manager
hdf5-manager
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
ruff format src/ tests/
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

## Distribution

- **PyPI** — `pip install hdf5-manager`
- **conda** — `conda env create -f environment.yml`
- **Windows .exe** — `nicegui-pack --onefile --name "HDF5-Manager" main.py`
- **GitHub Releases** — Pre-built .exe attached to each release

## License

MIT — see [LICENSE](LICENSE).
