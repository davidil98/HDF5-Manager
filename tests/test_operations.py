"""Tests for core.operations — HDF5 mutations."""

from __future__ import annotations

import tempfile

import h5py
import numpy as np

from hdf5_manager.core.operations import (
    copy_node,
    delete_node,
    merge_files,
    move_node,
    rename_node,
)


def _make_test_file() -> str:
    """Create a temporary HDF5 file with known structure."""
    tmp = tempfile.NamedTemporaryFile(suffix=".h5", delete=False)
    tmp.close()
    with h5py.File(tmp.name, "w") as f:
        f.create_group("group_a")
        grp = f.create_group("group_b")
        grp.create_dataset("dset_1", data=np.array([1, 2, 3]))
    return tmp.name


def test_rename_node() -> None:
    """Renaming a node should update its path."""
    path = _make_test_file()
    try:
        with h5py.File(path, "r+") as f:
            rename_node(f, "/group_a", "renamed_a")
            assert "renamed_a" in f
            assert "group_a" not in f
    finally:
        import os

        os.unlink(path)


def test_rename_dataset() -> None:
    """Renaming a dataset should update its path."""
    path = _make_test_file()
    try:
        with h5py.File(path, "r+") as f:
            rename_node(f, "/group_b/dset_1", "renamed_dset")
            assert "renamed_dset" in f["/group_b"]
            assert "dset_1" not in f["/group_b"]
    finally:
        import os

        os.unlink(path)


def test_delete_node() -> None:
    """Deleting a node should remove it from the file."""
    path = _make_test_file()
    try:
        with h5py.File(path, "r+") as f:
            delete_node(f, "/group_a")
            assert "group_a" not in f
            assert "group_b" in f
    finally:
        import os

        os.unlink(path)


def test_move_node() -> None:
    """Moving a node should relocate it."""
    path = _make_test_file()
    try:
        with h5py.File(path, "r+") as f:
            move_node(f, "/group_b/dset_1", "/group_a")
            assert "dset_1" in f["/group_a"]
            assert "dset_1" not in f["/group_b"]
    finally:
        import os

        os.unlink(path)


def test_copy_node() -> None:
    """Copying a node should duplicate it."""
    path = _make_test_file()
    try:
        with h5py.File(path, "r+") as f:
            copy_node(f, "/group_b/dset_1", "/group_a")
            assert "dset_1" in f["/group_a"]
            assert "dset_1" in f["/group_b"]
    finally:
        import os

        os.unlink(path)


def test_merge_files() -> None:
    """Merging should copy a node from source to dest file."""
    path_a = _make_test_file()
    path_b = _make_test_file()
    try:
        with h5py.File(path_a, "r") as src:
            with h5py.File(path_b, "r+") as dst:
                merge_files(src, "/group_b", dst, "/group_a")
        with h5py.File(path_b, "r") as dst:
            assert "group_b" in dst["/group_a"]
    finally:
        import os

        os.unlink(path_a)
        os.unlink(path_b)


def test_delete_root_raises() -> None:
    """Deleting the root group should raise ValueError."""
    path = _make_test_file()
    try:
        with h5py.File(path, "r+") as f:
            try:
                delete_node(f, "/")
            except ValueError:
                pass
            else:
                raise AssertionError("Expected ValueError")
    finally:
        import os

        os.unlink(path)


def test_rename_root_raises() -> None:
    """Renaming the root group should raise ValueError."""
    path = _make_test_file()
    try:
        with h5py.File(path, "r+") as f:
            try:
                rename_node(f, "/", "new_root")
            except ValueError:
                pass
            else:
                raise AssertionError("Expected ValueError")
    finally:
        import os

        os.unlink(path)
