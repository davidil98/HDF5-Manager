"""Export HDF5 datasets to CSV or Excel files.

Three export modes are supported:

1. ``side_by_side`` — One table per group, datasets placed side by side as columns.
2. ``sheets`` — One Excel workbook with a sheet per group containing its datasets.
3. ``per_group`` — One CSV/Excel file per group, each containing its datasets.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import h5py
import numpy as np
import pandas as pd

ExportMode = Literal["side_by_side", "sheets", "per_group"]


def _collect_datasets(group: h5py.Group) -> dict[str, np.ndarray]:
    """Collect all dataset arrays in a group (non-recursive).

    Returns:
        Dict mapping dataset name to its numpy array.
    """
    datasets: dict[str, np.ndarray] = {}
    for name in sorted(group.keys()):
        item = group[name]
        if isinstance(item, h5py.Dataset):
            datasets[name] = item[:]
    return datasets


def _build_dataframe(datasets: dict[str, np.ndarray]) -> pd.DataFrame:
    """Build a DataFrame from named datasets, padding shorter columns with NaN.

    Each dataset becomes a column. Columns of different lengths are padded.
    """
    if not datasets:
        return pd.DataFrame()
    max_len = max(len(v) for v in datasets.values())
    data = {}
    for name, arr in datasets.items():
        if arr.ndim == 1:
            data[name] = np.pad(arr, (0, max_len - len(arr)), constant_values=np.nan)
        else:
            for col_idx in range(arr.shape[1]):
                col_name = f"{name}[{col_idx}]" if arr.shape[1] > 1 else name
                col = arr[:, col_idx]
                padding = max_len - len(col)
                data[col_name] = np.pad(col, (0, padding), constant_values=np.nan)
    return pd.DataFrame(data)


def export_csv(
    h5file: h5py.File,
    group_paths: Sequence[str],
    mode: ExportMode,
    output_dir: str | Path,
) -> list[Path]:
    """Export groups to CSV.

    Args:
        h5file: An open h5py File in ``r`` mode.
        group_paths: List of absolute HDF5 group paths to export.
        mode: Export layout.
        output_dir: Directory to write output files.

    Returns:
        List of created file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    if mode == "side_by_side":
        for gpath in group_paths:
            datasets = _collect_datasets(h5file[gpath])
            df = _build_dataframe(datasets)
            if not df.empty:
                name = gpath.strip("/").replace("/", "_") or "root"
                path = output_dir / f"{name}.csv"
                df.to_csv(path, index=False)
                created.append(path)

    elif mode == "per_group":
        for gpath in group_paths:
            datasets = _collect_datasets(h5file[gpath])
            df = _build_dataframe(datasets)
            if not df.empty:
                name = gpath.strip("/").replace("/", "_") or "root"
                path = output_dir / f"{name}.csv"
                df.to_csv(path, index=False)
                created.append(path)

    elif mode == "sheets":
        raise NotImplementedError(
            "CSV does not support multi-sheet output. Use mode='side_by_side' "
            "or mode='per_group', or export_xlsx for sheets mode."
        )

    return created


def export_xlsx(
    h5file: h5py.File,
    group_paths: Sequence[str],
    mode: ExportMode,
    output_dir: str | Path,
    workbook_name: str = "export.xlsx",
) -> list[Path]:
    """Export groups to Excel (.xlsx).

    Args:
        h5file: An open h5py File in ``r`` mode.
        group_paths: List of absolute HDF5 group paths to export.
        mode: Export layout.
        output_dir: Directory to write output files.
        workbook_name: Filename for ``sheets`` and ``side_by_side`` modes
            (when writing a single workbook).

    Returns:
        List of created file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    if mode == "side_by_side":
        sheets: dict[str, pd.DataFrame] = {}
        for gpath in group_paths:
            datasets = _collect_datasets(h5file[gpath])
            df = _build_dataframe(datasets)
            if not df.empty:
                name = gpath.strip("/").replace("/", "_") or "root"
                sheets[name[:31]] = df  # Excel sheet names max 31 chars

        if sheets:
            path = output_dir / workbook_name
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                for sheet_name, df in sheets.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            created.append(path)

    elif mode == "sheets":
        for gpath in group_paths:
            datasets = _collect_datasets(h5file[gpath])
            df = _build_dataframe(datasets)
            if not df.empty:
                name = gpath.strip("/").replace("/", "_") or "root"
                path = output_dir / f"{name}.xlsx"
                with pd.ExcelWriter(path, engine="openpyxl") as writer:
                    for dset_name, arr in datasets.items():
                        sheet_name = dset_name[:31]
                        if arr.ndim == 1:
                            pd.DataFrame(arr).to_excel(
                                writer, sheet_name=sheet_name, index=False
                            )
                        else:
                            pd.DataFrame(arr).to_excel(
                                writer, sheet_name=sheet_name, index=False
                            )
                created.append(path)

    elif mode == "per_group":
        for gpath in group_paths:
            datasets = _collect_datasets(h5file[gpath])
            df = _build_dataframe(datasets)
            if not df.empty:
                name = gpath.strip("/").replace("/", "_") or "root"
                path = output_dir / f"{name}.xlsx"
                df.to_excel(path, index=False)
                created.append(path)

    return created
