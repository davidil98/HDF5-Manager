"""Tests for core.export — CSV and Excel export."""

from __future__ import annotations

import tempfile
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

from hdf5_manager.core.export import export_csv, export_xlsx


def _make_test_file() -> str:
    """Create a temporary HDF5 file with test data."""
    tmp = tempfile.NamedTemporaryFile(suffix=".h5", delete=False)
    tmp.close()
    with h5py.File(tmp.name, "w") as f:
        grp = f.create_group("sweeps")
        sub = grp.create_group("curve_000")
        sub.create_dataset("voltage", data=np.array([0.0, 0.5, 1.0, 1.5, 2.0]))
        sub.create_dataset("current", data=np.array([1e-6, 2e-6, 5e-6, 1e-5, 2e-5]))
    return tmp.name


def test_export_csv_side_by_side() -> None:
    """Export should create one CSV per group with datasets as columns."""
    path = _make_test_file()
    output_dir = tempfile.mkdtemp()
    try:
        with h5py.File(path, "r") as f:
            files = export_csv(
                f, ["/sweeps/curve_000"], mode="side_by_side", output_dir=output_dir
            )
        assert len(files) == 1
        assert files[0].suffix == ".csv"
        df = pd.read_csv(files[0])
        assert "voltage" in df.columns
        assert "current" in df.columns
        assert len(df) == 5
    finally:
        import os
        import shutil

        os.unlink(path)
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_csv_per_group() -> None:
    """per_group mode should create one CSV per group."""
    path = _make_test_file()
    output_dir = tempfile.mkdtemp()
    try:
        with h5py.File(path, "r") as f:
            files = export_csv(
                f, ["/sweeps/curve_000"], mode="per_group", output_dir=output_dir
            )
        assert len(files) == 1
        df = pd.read_csv(files[0])
        assert "voltage" in df.columns
    finally:
        import os
        import shutil

        os.unlink(path)
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_xlsx_side_by_side() -> None:
    """side_by_side XLSX should create a workbook with one sheet per group."""
    path = _make_test_file()
    output_dir = tempfile.mkdtemp()
    try:
        with h5py.File(path, "r") as f:
            files = export_xlsx(
                f,
                ["/sweeps/curve_000"],
                mode="side_by_side",
                output_dir=output_dir,
                workbook_name="test.xlsx",
            )
        assert len(files) == 1
        assert files[0].suffix == ".xlsx"
        df = pd.read_excel(files[0])
        assert "voltage" in df.columns
    finally:
        import os
        import shutil

        os.unlink(path)
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_xlsx_per_group() -> None:
    """per_group XLSX should create one file per group."""
    path = _make_test_file()
    output_dir = tempfile.mkdtemp()
    try:
        with h5py.File(path, "r") as f:
            files = export_xlsx(
                f,
                ["/sweeps/curve_000"],
                mode="per_group",
                output_dir=output_dir,
            )
        assert len(files) == 1
        assert files[0].suffix == ".xlsx"
    finally:
        import os
        import shutil

        os.unlink(path)
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_xlsx_sheets_per_dataset() -> None:
    """sheets mode should put each dataset in its own sheet."""
    path = _make_test_file()
    output_dir = Path(tempfile.mkdtemp())
    try:
        with h5py.File(path, "r") as f:
            files = export_xlsx(
                f,
                ["/sweeps/curve_000"],
                mode="sheets",
                output_dir=output_dir,
            )
        assert len(files) == 1
        xl = pd.ExcelFile(files[0])
        sheet_names = xl.sheet_names
        assert "voltage" in sheet_names or "current" in sheet_names
        assert len(sheet_names) >= 1
    finally:
        import os
        import shutil

        os.unlink(path)
        shutil.rmtree(str(output_dir), ignore_errors=True)


def test_export_csv_sheets_raises() -> None:
    """CSV export with 'sheets' mode should raise NotImplementedError."""
    path = _make_test_file()
    output_dir = tempfile.mkdtemp()
    try:
        with h5py.File(path, "r") as f:
            try:
                export_csv(
                    f, ["/sweeps/curve_000"], mode="sheets", output_dir=output_dir
                )
            except NotImplementedError:
                pass
            else:
                raise AssertionError("Expected NotImplementedError")
    finally:
        import os
        import shutil

        os.unlink(path)
        shutil.rmtree(output_dir, ignore_errors=True)
