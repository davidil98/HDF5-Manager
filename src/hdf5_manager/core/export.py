"""Export HDF5 datasets to CSV or Excel files.

Three export modes are supported:

1. ``side_by_side`` -- One file containing all selected datasets as columns.
2. ``sheets`` -- One Excel workbook with one sheet per selected group.
3. ``per_group`` -- One CSV/Excel file per selected group, each containing
   its direct datasets.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import h5py
import numpy as np
import pandas as pd

ExportMode = Literal["side_by_side", "sheets", "per_group"]

_INVALID_SHEET_CHARS = re.compile(r"[\\/*?:\[\]]")


def _collect_datasets(group: h5py.Group) -> dict[str, np.ndarray]:
    """Collect direct dataset arrays in a group.

    Returns:
        Dict mapping dataset name to its numpy array.
    """
    datasets: dict[str, np.ndarray] = {}
    for name in sorted(group.keys()):
        item = group[name]
        if isinstance(item, h5py.Dataset):
            datasets[name] = item[:]
    return datasets


def _collect_selected_datasets(
    h5file: h5py.File, group_paths: Sequence[str]
) -> dict[str, np.ndarray]:
    """Collect datasets recursively, keyed by their full HDF5 path.

    If both a parent group and one of its descendants are selected, the
    dataset is still returned only once.
    """
    datasets: dict[str, np.ndarray] = {}
    visited: set[str] = set()

    def walk(group: h5py.Group) -> None:
        for name in sorted(group.keys()):
            item = group[name]
            if isinstance(item, h5py.Dataset):
                if item.name in visited:
                    continue
                visited.add(item.name)
                datasets[_path_to_name(item.name)] = item[:]
            elif isinstance(item, h5py.Group):
                walk(item)

    for group_path in group_paths:
        walk(h5file[group_path])
    return datasets


def _path_to_name(path: str) -> str:
    """Convert an absolute HDF5 path into a flat output name."""
    return path.strip("/").replace("/", "_") or "root"


def _pad_column(arr: np.ndarray, target_len: int) -> np.ndarray:
    """Pad *arr* to *target_len* using a dtype-appropriate fill value.

    Float arrays are padded with ``np.nan``. Integer and boolean arrays use
    ``pd.array`` with a nullable dtype so that the fill value is ``pd.NA``
    instead of ``np.nan``, which cannot be stored in a NumPy integer array.
    """
    padding = target_len - len(arr)
    if padding <= 0:
        return arr
    if np.issubdtype(arr.dtype, np.floating):
        return np.pad(arr, (0, padding), constant_values=np.nan)
    if np.issubdtype(arr.dtype, np.integer):
        padded = pd.array(arr.tolist() + [pd.NA] * padding, dtype=pd.Int64Dtype())
        return padded
    if np.issubdtype(arr.dtype, np.bool_):
        padded = pd.array(arr.tolist() + [pd.NA] * padding, dtype=pd.BooleanDtype())
        return padded
    return np.pad(arr, (0, padding), constant_values=None)


def _build_dataframe(datasets: dict[str, np.ndarray]) -> pd.DataFrame:
    """Build a DataFrame from named datasets, padding shorter columns."""
    if not datasets:
        return pd.DataFrame()

    normalised = {
        name: np.asarray(arr).reshape(1) if np.asarray(arr).ndim == 0 else arr
        for name, arr in datasets.items()
    }
    max_len = max(len(value) for value in normalised.values())
    data: dict[str, Any] = {}
    used_columns: set[str] = set()

    for name, arr in normalised.items():
        if arr.ndim == 1:
            column_name = _unique_name(name, used_columns)
            data[column_name] = _pad_column(arr, max_len)
        else:
            for col_idx in range(arr.shape[1]):
                base_name = f"{name}[{col_idx}]" if arr.shape[1] > 1 else name
                column_name = _unique_name(base_name, used_columns)
                data[column_name] = _pad_column(arr[:, col_idx], max_len)
    return pd.DataFrame(data)


def _unique_name(name: str, used: set[str]) -> str:
    """Return a deterministic name that does not collide with existing names."""
    candidate = name
    index = 2
    while candidate in used:
        candidate = f"{name}_{index}"
        index += 1
    used.add(candidate)
    return candidate


def _normalise_filename(filename: str, suffix: str) -> str:
    """Keep an output filename inside the configured output directory."""
    safe_name = Path(filename.strip()).name
    if safe_name in {"", ".", ".."}:
        safe_name = f"export{suffix}"
    if Path(safe_name).suffix.lower() != suffix:
        safe_name = f"{safe_name}{suffix}"
    return safe_name


def _group_filename(group_path: str, suffix: str) -> str:
    """Build the automatic filename used by ``per_group``."""
    return f"{_path_to_name(group_path)}{suffix}"


def _unique_sheet_name(name: str, used: set[str]) -> str:
    """Create a valid, unique Excel sheet name from a dataset path."""
    base = _INVALID_SHEET_CHARS.sub("_", name).strip() or "dataset"
    base = base[:31]
    candidate = base
    index = 2
    while candidate in used:
        suffix = f"_{index}"
        candidate = f"{base[: 31 - len(suffix)]}{suffix}"
        index += 1
    used.add(candidate)
    return candidate





def export_csv(
    h5file: h5py.File,
    group_paths: Sequence[str],
    mode: ExportMode,
    output_dir: str | Path,
    output_name: str = "export.csv",
) -> list[Path]:
    """Export groups to CSV.

    ``side_by_side`` writes one combined CSV using all selected datasets.
    ``per_group`` writes one CSV per selected group using direct datasets.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if mode == "sheets":
        raise NotImplementedError(
            "CSV does not support one sheet per group. Use Excel for sheets mode."
        )

    if mode == "side_by_side":
        dataframe = _build_dataframe(_collect_selected_datasets(h5file, group_paths))
        if dataframe.empty:
            return []
        path = output_dir / _normalise_filename(output_name, ".csv")
        dataframe.to_csv(path, index=False)
        return [path]

    created: list[Path] = []
    for group_path in group_paths:
        dataframe = _build_dataframe(_collect_datasets(h5file[group_path]))
        if dataframe.empty:
            continue
        path = output_dir / _group_filename(group_path, ".csv")
        dataframe.to_csv(path, index=False)
        created.append(path)
    return created


def export_xlsx(
    h5file: h5py.File,
    group_paths: Sequence[str],
    mode: ExportMode,
    output_dir: str | Path,
    workbook_name: str = "export.xlsx",
) -> list[Path]:
    """Export groups to Excel (.xlsx).

    ``side_by_side`` writes one worksheet containing all selected datasets.
    ``sheets`` writes one worksheet per selected group, with its direct
    datasets as columns. ``per_group`` keeps one workbook per selected
    group with its direct datasets as columns.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    workbook_name = _normalise_filename(workbook_name, ".xlsx")

    if mode == "side_by_side":
        dataframe = _build_dataframe(_collect_selected_datasets(h5file, group_paths))
        if dataframe.empty:
            return []
        path = output_dir / workbook_name
        dataframe.to_excel(path, sheet_name="data", index=False)
        return [path]

    if mode == "sheets":
        used_sheet_names: set[str] = set()
        has_data = False
        path = output_dir / workbook_name
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for group_path in group_paths:
                datasets = _collect_datasets(h5file[group_path])
                if not datasets:
                    continue
                has_data = True
                sheet_name = _unique_sheet_name(
                    _path_to_name(group_path), used_sheet_names
                )
                _build_dataframe(datasets).to_excel(
                    writer, sheet_name=sheet_name, index=False
                )
        return [path] if has_data else []

    created: list[Path] = []
    for group_path in group_paths:
        dataframe = _build_dataframe(_collect_datasets(h5file[group_path]))
        if dataframe.empty:
            continue
        path = output_dir / _group_filename(group_path, ".xlsx")
        dataframe.to_excel(path, index=False)
        created.append(path)
    return created
