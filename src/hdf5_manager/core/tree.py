"""Build hierarchical tree representation of an HDF5 file.

The tree uses a dict format compatible with NiceGUI's ``ui.tree``:

    {
        "id": "/path/to/group",
        "label": "group_name",
        "children": [...],
        "type": "group" | "dataset",
        "attributes": {attribute_name: value},
        "shape": "(100, 3)",
        "dtype": "float64",
    }
"""

from __future__ import annotations

from typing import Any

import h5py
import numpy as np


def build_tree(h5file: h5py.File) -> list[dict[str, Any]]:
    """Build a tree representation of the entire HDF5 file.

    Args:
        h5file: An open h5py File or Group object.

    Returns:
        List of tree node dicts representing the root-level contents.
    """
    return _walk_group(h5file)


def _walk_group(group: h5py.Group) -> list[dict[str, Any]]:
    """Recursively walk an HDF5 group and return its tree representation."""
    nodes: list[dict[str, Any]] = []
    for name in sorted(group.keys()):
        item = group[name]
        if isinstance(item, h5py.Group):
            node: dict[str, Any] = {
                "id": item.name,
                "label": name,
                "children": _walk_group(item),
                "type": "group",
                "attributes": dict(item.attrs) if item.attrs else {},
                "shape": "",
                "dtype": "",
            }
        else:
            node = {
                "id": item.name,
                "label": name,
                "children": [],
                "type": "dataset",
                "shape": str(item.shape),
                "dtype": str(item.dtype),
            }
        nodes.append(node)
    return nodes


def _attr_to_python(value) -> str | int | float | bool | list | dict | None:
    """Convert h5py/numpy attribute values to Python types that JSON/UI can serialize.

    Handles both scalar values (e.g. an individual cell extracted from a
    dataset) and array values (e.g. an attribute stored as a numpy array).
    """
    if isinstance(value, np.ndarray):  # arrays → list
        return value.tolist()
    if isinstance(value, (bytes, np.bytes_)):  # bytes / numpy bytes
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.str_):  # numpy string scalar
        return str(value)
    if isinstance(value, np.integer):  # integer 32/64
        return int(value)
    if isinstance(value, np.floating):  # float 32/64
        return float(value)
    if isinstance(value, np.bool_):  # boolean
        return bool(value)
    return value  # already a native Python type


def get_node(h5file: h5py.File, path: str) -> h5py.Group | h5py.Dataset:
    """Resolve a path to an HDF5 group or dataset object.

    Args:
        h5file: An open h5py File.
        path: Absolute HDF5 path (e.g. ``/group/dataset``).

    Returns:
        The h5py Group or Dataset at *path*.

    Raises:
        KeyError: If *path* does not exist.
    """
    return h5file[path]
