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
    """Side-by-side CSV should combine all selected datasets in one file."""
    path = _make_test_file()
    output_dir = tempfile.mkdtemp()
    try:
        with h5py.File(path, "r") as f:
            files = export_csv(
                f,
                ["/sweeps"],
                mode="side_by_side",
                output_dir=output_dir,
                output_name="combined.csv",
            )
        assert len(files) == 1
        assert files[0].name == "combined.csv"
        assert files[0].suffix == ".csv"
        df = pd.read_csv(files[0])
        assert "sweeps_curve_000_voltage" in df.columns
        assert "sweeps_curve_000_current" in df.columns
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
    """Side-by-side XLSX should combine all datasets in one worksheet."""
    path = _make_test_file()
    output_dir = tempfile.mkdtemp()
    try:
        with h5py.File(path, "r") as f:
            files = export_xlsx(
                f,
                ["/sweeps"],
                mode="side_by_side",
                output_dir=output_dir,
                workbook_name="test.xlsx",
            )
        assert len(files) == 1
        assert files[0].suffix == ".xlsx"
        df = pd.read_excel(files[0])
        assert "sweeps_curve_000_voltage" in df.columns
        assert pd.ExcelFile(files[0]).sheet_names == ["data"]
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


def test_export_xlsx_sheets_per_group() -> None:
    """Sheets mode should put each selected group in its own worksheet."""
    path = _make_test_file()
    output_dir = Path(tempfile.mkdtemp())
    try:
        with h5py.File(path, "r") as f:
            files = export_xlsx(
                f,
                ["/sweeps/curve_000"],
                mode="sheets",
                output_dir=output_dir,
                workbook_name="groups.xlsx",
            )
        assert len(files) == 1
        assert files[0].name == "groups.xlsx"
        xl = pd.ExcelFile(files[0])
        sheet_names = xl.sheet_names
        assert len(sheet_names) == 1
        assert "sweeps_curve_000" in sheet_names
        df = xl.parse(sheet_names[0])
        assert "voltage" in df.columns
        assert "current" in df.columns
    finally:
        import os
        import shutil

        os.unlink(path)
        shutil.rmtree(str(output_dir), ignore_errors=True)


def test_export_xlsx_sheets_multiple_groups() -> None:
    """Sheets mode with multiple groups should create one sheet per group."""
    tmp = tempfile.NamedTemporaryFile(suffix=".h5", delete=False)
    tmp.close()
    with h5py.File(tmp.name, "w") as f:
        g1 = f.create_group("group_a")
        g1.create_dataset("x", data=np.array([1.0, 2.0]))
        g1.create_dataset("y", data=np.array([3.0, 4.0]))
        g2 = f.create_group("group_b")
        g2.create_dataset("z", data=np.array([5.0, 6.0]))
    output_dir = Path(tempfile.mkdtemp())
    try:
        with h5py.File(tmp.name, "r") as f:
            files = export_xlsx(
                f,
                ["/group_a", "/group_b"],
                mode="sheets",
                output_dir=output_dir,
                workbook_name="multi.xlsx",
            )
        assert len(files) == 1
        xl = pd.ExcelFile(files[0])
        assert set(xl.sheet_names) == {"group_a", "group_b"}
        df_a = xl.parse("group_a")
        assert "x" in df_a.columns
        assert "y" in df_a.columns
        df_b = xl.parse("group_b")
        assert "z" in df_b.columns
    finally:
        import os
        import shutil

        os.unlink(tmp.name)
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


def test_export_csv_side_by_side_deduplicates_nested_group_selection() -> None:
    """Selecting a group and its child must not duplicate dataset columns."""
    path = _make_test_file()
    output_dir = tempfile.mkdtemp()
    try:
        with h5py.File(path, "r") as f:
            files = export_csv(
                f,
                ["/sweeps", "/sweeps/curve_000"],
                mode="side_by_side",
                output_dir=output_dir,
            )
        df = pd.read_csv(files[0])
        assert list(df.columns).count("sweeps_curve_000_voltage") == 1
    finally:
        import os
        import shutil

        os.unlink(path)
        shutil.rmtree(output_dir, ignore_errors=True)

