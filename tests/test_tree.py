"""Tests for core.tree — HDF5 tree building."""

from __future__ import annotations

import tempfile

import h5py
import numpy as np

from hdf5_manager.core.tree import build_tree, get_node


def test_build_tree_empty_file() -> None:
    """Tree of an empty HDF5 file should be an empty list."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=True) as tmp:
        with h5py.File(tmp.name, "w") as f:
            tree = build_tree(f)
        assert tree == []


def test_build_tree_with_groups_and_datasets() -> None:
    """Tree should reflect the HDF5 hierarchy."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=True) as tmp:
        with h5py.File(tmp.name, "w") as f:
            f.create_group("group_a")
            f.create_dataset("dset_1", data=np.array([1, 2, 3]))
            grp = f.create_group("group_b")
            grp.create_dataset("dset_2", data=np.array([[1, 2], [3, 4]]))

            tree = build_tree(f)

            assert len(tree) == 3

            dset_1 = tree[0]
            assert dset_1["type"] == "dataset"
            assert dset_1["id"] == "/dset_1"
            assert dset_1["shape"] == "(3,)"
            assert dset_1["dtype"] == "int64"

            group_a = tree[1]
            assert group_a["type"] == "group"
            assert group_a["id"] == "/group_a"
            assert group_a["children"] == []

            group_b = tree[2]
            assert group_b["type"] == "group"
            assert len(group_b["children"]) == 1
            assert group_b["children"][0]["id"] == "/group_b/dset_2"
            assert group_b["children"][0]["shape"] == "(2, 2)"


def test_get_node() -> None:
    """get_node should return the correct h5py object."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=True) as tmp:
        with h5py.File(tmp.name, "w") as f:
            f.create_group("stuff")
            f.create_dataset("data", data=np.array([5.0]))

            assert isinstance(get_node(f, "/stuff"), h5py.Group)
            assert isinstance(get_node(f, "/data"), h5py.Dataset)
            assert get_node(f, "/data")[0] == 5.0
