"""Tests for core.operations — HDF5 mutations."""

from __future__ import annotations

import tempfile

import h5py
import numpy as np

from hdf5_manager.core.operations import (
    apply_changes,
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


# ── apply_changes ──────────────────────────────────────────────────


def test_apply_changes_rename_and_delete() -> None:
    """apply_changes should copy source to output and apply all changes."""
    import os

    source = _make_test_file()
    output = tempfile.mkdtemp()
    output_path = os.path.join(output, "output.h5")
    try:
        changes = [
            {"action": "rename", "path": "/group_a", "new_name": "renamed_a"},
            {"action": "delete", "path": "/group_b"},
        ]
        apply_changes(source, changes, output_path, overwrite=False)

        # Source should be untouched.
        with h5py.File(source, "r") as f:
            assert "group_a" in f
            assert "group_b" in f

        # Output should reflect both changes.
        with h5py.File(output_path, "r") as f:
            assert "renamed_a" in f
            assert "group_a" not in f
            assert "group_b" not in f
    finally:
        os.unlink(source)
        os.unlink(output_path)
        os.rmdir(output)


def test_apply_changes_refuses_overwrite() -> None:
    """FileExistsError when output exists and overwrite=False."""
    import os

    source = _make_test_file()
    output_dir = tempfile.mkdtemp()
    output_path = os.path.join(output_dir, "output.h5")
    # Pre-create the output file (simulate existing file).
    with open(output_path, "wb") as f:
        f.write(b"existing")
    try:
        changes = [{"action": "rename", "path": "/group_a", "new_name": "x"}]
        try:
            apply_changes(source, changes, output_path, overwrite=False)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Expected FileExistsError")
    finally:
        os.unlink(source)
        os.unlink(output_path)
        os.rmdir(output_dir)


def test_apply_changes_overwrite_true() -> None:
    """overwrite=True should replace existing output without error."""
    import os

    source = _make_test_file()
    output_dir = tempfile.mkdtemp()
    output_path = os.path.join(output_dir, "output.h5")
    with open(output_path, "wb") as f:
        f.write(b"existing")
    try:
        changes = [{"action": "rename", "path": "/group_a", "new_name": "renamed"}]
        apply_changes(source, changes, output_path, overwrite=True)
        with h5py.File(output_path, "r") as f:
            assert "renamed" in f
    finally:
        os.unlink(source)
        os.unlink(output_path)
        os.rmdir(output_dir)


def test_apply_changes_invalid_action() -> None:
    """ValueError for an unknown action type."""
    import os

    source = _make_test_file()
    output_dir = tempfile.mkdtemp()
    output_path = os.path.join(output_dir, "output.h5")
    try:
        try:
            apply_changes(
                source,
                [{"action": "frobnicate", "path": "/group_a"}],
                output_path,
                overwrite=False,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")
    finally:
        os.unlink(source)
        os.unlink(output_path)
        os.rmdir(output_dir)


def test_apply_changes_empty_list() -> None:
    """Empty changes list is a no-op (just copies the file)."""
    import os

    source = _make_test_file()
    output_dir = tempfile.mkdtemp()
    output_path = os.path.join(output_dir, "output.h5")
    try:
        apply_changes(source, [], output_path, overwrite=False)
        with h5py.File(output_path, "r") as f:
            assert "group_a" in f
            assert "group_b" in f
    finally:
        os.unlink(source)
        os.unlink(output_path)
        os.rmdir(output_dir)


def test_apply_changes_missing_path() -> None:
    """ValueError when rename change has no new_name, delete has no path."""
    import os

    source = _make_test_file()
    output_dir = tempfile.mkdtemp()
    output_path = os.path.join(output_dir, "output.h5")
    try:
        try:
            apply_changes(
                source,
                [{"action": "rename", "path": "/group_a"}],
                output_path,
                overwrite=False,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")
    finally:
        os.unlink(source)
        os.unlink(output_path)
        os.rmdir(output_dir)
