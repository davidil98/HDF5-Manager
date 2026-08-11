"""Tests for core.operations — HDF5 mutations."""

from __future__ import annotations

import glob
import os
import tempfile

import h5py
import numpy as np

from hdf5_manager.core.operations import (
    apply_changes,
    copy_node,
    default_output_path,
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
        if os.path.exists(output_path):
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
        if os.path.exists(output_path):
            os.unlink(output_path)
        os.rmdir(output_dir)


def test_default_output_path() -> None:
    """Naming helper inserts -edit before the extension."""
    assert default_output_path("/data/foo.h5") == "/data/foo-edit.h5"
    assert default_output_path("/data/foo.hdf5") == "/data/foo-edit.hdf5"
    assert default_output_path("/data/foo") == "/data/foo-edit"
    assert default_output_path("foo.h5") == "foo-edit.h5"


def test_apply_changes_in_place_overwrite() -> None:
    """When output_path == source_path the source is replaced atomically.

    The source must end up with the changes applied, not corrupted.
    """
    source = _make_test_file()
    try:
        changes = [{"action": "rename", "path": "/group_a", "new_name": "renamed"}]
        apply_changes(source, changes, source, overwrite=True)
        with h5py.File(source, "r") as f:
            assert "renamed" in f
            assert "group_a" not in f
    finally:
        os.unlink(source)


def test_apply_changes_cleans_up_temp_on_failure() -> None:
    """If a change raises mid-flight, no residual temp file is left behind."""
    source = _make_test_file()
    output_dir = tempfile.mkdtemp()
    output_path = os.path.join(output_dir, "out.h5")
    try:
        # Force a failure: reference a path that does not exist.
        changes = [{"action": "delete", "path": "/nonexistent_group"}]
        try:
            apply_changes(source, changes, output_path, overwrite=False)
        except KeyError:
            pass
        else:
            raise AssertionError("Expected KeyError")

        # Output must not be created and no temp file should linger.
        assert not os.path.exists(output_path)
        temps = glob.glob(os.path.join(output_dir, ".hdf5_apply_*"))
        assert temps == [], f"Leftover temp files: {temps}"
    finally:
        os.unlink(source)
        os.rmdir(output_dir)


def test_unique_sibling_name_no_collision() -> None:
    """Returns the requested name unchanged when there is no collision."""
    from hdf5_manager.web_gui.editor import _unique_sibling_name

    siblings = {"other", "data_edit"}
    assert _unique_sibling_name(siblings, "current", "fresh") == "fresh"


def test_unique_sibling_name_no_op_rename_allowed() -> None:
    """Renaming a node to its own current label is accepted as-is."""
    from hdf5_manager.web_gui.editor import _unique_sibling_name

    siblings = {"data"}
    assert _unique_sibling_name(siblings, "data", "data") == "data"


def test_unique_sibling_name_appends_edit() -> None:
    """First collision appends _edit; chained collisions chain _edit."""
    from hdf5_manager.web_gui.editor import _unique_sibling_name

    siblings = {"data"}
    assert _unique_sibling_name(siblings, "other", "data") == "data_edit"

    siblings = {"data", "data_edit"}
    assert _unique_sibling_name(siblings, "other", "data") == "data_edit_edit"


def test_rename_node_raises_on_collision() -> None:
    """Backend defensive check refuses to clobber an existing sibling."""
    path = _make_test_file()
    try:
        with h5py.File(path, "r+") as f:
            # Both /group_a and /group_b exist at root.
            try:
                rename_node(f, "/group_a", "group_b")
            except ValueError:
                pass
            else:
                raise AssertionError("Expected ValueError on collision")
            # Both groups still exist after the rejected rename.
            assert "group_a" in f
            assert "group_b" in f
    finally:
        os.unlink(path)


def _make_nested_test_file() -> str:
    """Create a file with a parent group containing a child dataset."""
    tmp = tempfile.NamedTemporaryFile(suffix=".h5", delete=False)
    tmp.close()
    with h5py.File(tmp.name, "w") as f:
        grp = f.create_group("Batch1_Dispositivo1_Output1_00")
        grp.create_dataset("curve_010", data=np.array([1, 2, 3]))
    return tmp.name


def test_virtual_rename_rebases_child_paths() -> None:
    """Renaming a parent must also rewrite its children's ids."""
    from hdf5_manager.web_gui.editor import apply_virtual_changes

    raw_tree = [
        {
            "id": "/Batch1_Dispositivo1_Output1_00",
            "label": "Batch1_Dispositivo1_Output1_00",
            "children": [
                {
                    "id": "/Batch1_Dispositivo1_Output1_00/curve_010",
                    "label": "curve_010",
                    "children": [],
                    "type": "dataset",
                }
            ],
            "type": "group",
        }
    ]
    pending = [
        {
            "action": "rename",
            "path": "/Batch1_Dispositivo1_Output1_00",
            "new_name": "Batch1_dispositivo1_Output2_00_edit",
        }
    ]
    new_tree = apply_virtual_changes(raw_tree, pending)
    parent = new_tree[0]
    assert parent["id"] == "/Batch1_dispositivo1_Output2_00_edit"
    assert parent["label"] == "Batch1_dispositivo1_Output2_00_edit"
    child = parent["children"][0]
    assert child["id"] == "/Batch1_dispositivo1_Output2_00_edit/curve_010"


def test_apply_changes_parent_then_child() -> None:
    """End-to-end: rename a parent, then a child, both must apply cleanly."""
    source = _make_nested_test_file()
    output_dir = tempfile.mkdtemp()
    output = os.path.join(output_dir, "out.h5")
    try:
        # Simulate the user selecting the parent, renaming, then selecting
        # the child (now under its new path) and renaming it.
        changes = [
            {
                "action": "rename",
                "path": "/Batch1_Dispositivo1_Output1_00",
                "new_name": "Batch1_dispositivo1_Output2_00_edit",
            },
            {
                "action": "rename",
                "path": "/Batch1_dispositivo1_Output2_00_edit/curve_010",
                "new_name": "curve_000",
            },
        ]
        apply_changes(source, changes, output, overwrite=False)

        with h5py.File(output, "r") as f:
            assert "Batch1_Dispositivo1_Output1_00" not in f
            assert "Batch1_dispositivo1_Output2_00_edit" in f
            assert "curve_010" not in f["/Batch1_dispositivo1_Output2_00_edit"]
            assert "curve_000" in f["/Batch1_dispositivo1_Output2_00_edit"]
    finally:
        os.unlink(source)
        os.unlink(output)
        os.rmdir(output_dir)


def test_apply_changes_child_then_parent() -> None:
    """The reverse order (child first, parent second) must also work."""
    source = _make_nested_test_file()
    output_dir = tempfile.mkdtemp()
    output = os.path.join(output_dir, "out.h5")
    try:
        # The child's original path is still valid before the parent rename.
        changes = [
            {
                "action": "rename",
                "path": "/Batch1_Dispositivo1_Output1_00/curve_010",
                "new_name": "curve_000",
            },
            {
                "action": "rename",
                "path": "/Batch1_Dispositivo1_Output1_00",
                "new_name": "Batch1_dispositivo1_Output2_00_edit",
            },
        ]
        apply_changes(source, changes, output, overwrite=False)

        with h5py.File(output, "r") as f:
            assert "Batch1_dispositivo1_Output2_00_edit" in f
            assert "curve_000" in f["/Batch1_dispositivo1_Output2_00_edit"]
    finally:
        os.unlink(source)
        os.unlink(output)
        os.rmdir(output_dir)
