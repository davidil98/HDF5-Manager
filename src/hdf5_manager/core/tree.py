"""Build hierarchical tree representation of an HDF5 file.

The tree uses a dict format compatible with NiceGUI's ``ui.tree``:

    {
        "id": "/path/to/group",
        "label": "group_name",
        "children": [...],
        "type": "group" | "dataset",
        "shape": "(100, 3)",
        "dtype": "float64",
    }
"""

from __future__ import annotations

from typing import Any

import h5py


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
