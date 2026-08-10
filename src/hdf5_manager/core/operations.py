"""HDF5 file mutation operations: rename, delete, copy, move, merge."""

from __future__ import annotations

import os
import shutil
from typing import Any

import h5py


def rename_node(h5file: h5py.File, path: str, new_name: str) -> None:
    """Rename a group or dataset within the same parent.

    Args:
        h5file: An open h5py File (mode ``r+`` or ``a``).
        path: Absolute HDF5 path to the node to rename.
        new_name: New basename for the node.

    Raises:
        ValueError: If *path* is the root group.
    """
    if path == "/":
        raise ValueError("Cannot rename the root group")
    parent_path, _old_name = os.path.split(path)
    h5file[parent_path].move(path, new_name)


def delete_node(h5file: h5py.File, path: str) -> None:
    """Delete a group or dataset.

    Args:
        h5file: An open h5py File (mode ``r+`` or ``a``).
        path: Absolute HDF5 path to the node to delete.

    Raises:
        ValueError: If *path* is the root group.
    """
    if path == "/":
        raise ValueError("Cannot delete the root group")
    parent_path, name = os.path.split(path)
    del h5file[parent_path][name]


def move_node(h5file: h5py.File, source_path: str, dest_parent: str) -> None:
    """Move a group or dataset to a different parent group.

    Args:
        h5file: An open h5py File (mode ``r+`` or ``a``).
        source_path: Absolute path of the node to move.
        dest_parent: Absolute path of the destination parent group.
    """
    h5file[dest_parent].move(source_path, os.path.basename(source_path))


def copy_node(
    h5file: h5py.File,
    source_path: str,
    dest_parent: str,
    new_name: str | None = None,
) -> None:
    """Copy a group or dataset to another location within the same file.

    Args:
        h5file: An open h5py File (mode ``r+`` or ``a``).
        source_path: Absolute path of the node to copy.
        dest_parent: Absolute path of the destination parent group.
        new_name: Optional new name; defaults to the original basename.
    """
    dest = h5file[dest_parent]
    h5file[dest.name].copy(source_path, dest, name=new_name)


def merge_files(
    source: h5py.File,
    source_path: str,
    dest: h5py.File,
    dest_parent: str = "/",
    new_name: str | None = None,
) -> None:
    """Copy a group or dataset from *source* into *dest*.

    Args:
        source: Source HDF5 file open in ``r`` mode.
        source_path: Path within *source* to copy.
        dest: Destination HDF5 file open in ``r+`` mode.
        dest_parent: Destination parent path in *dest*.
        new_name: Optional new name; defaults to original basename.
    """
    dest[dest_parent].copy(source[source_path], dest[dest_parent], name=new_name)


def create_group(h5file: h5py.File, parent_path: str, name: str) -> h5py.Group:
    """Create a new group.

    Args:
        h5file: An open h5py File (mode ``r+``, ``a``, or ``w``).
        parent_path: Absolute path of the parent group.
        name: Name for the new group.

    Returns:
        The newly created Group.
    """
    return h5file[parent_path].create_group(name)


def apply_changes(
    source_path: str,
    changes: list[dict[str, Any]],
    output_path: str,
    overwrite: bool = False,
) -> None:
    """Apply a batch of pending changes from source to a new output file.

    The workflow is:

    1. Copy *source_path* to *output_path* (preserves the original).
    2. Open *output_path* in ``r+`` mode and apply each change in order.

    The source file is never modified. If *output_path* already exists,
    the call refuses unless *overwrite* is True.

    Args:
        source_path: Path to the source HDF5 file.
        changes: List of change dicts. Each must contain:

            - ``{"action": "rename", "path": str, "new_name": str}``
            - ``{"action": "delete", "path": str}``

        output_path: Destination path. Created by the function.
        overwrite: If True, replace existing *output_path*.

    Raises:
        FileExistsError: If *output_path* exists and *overwrite* is False.
        ValueError: If a change dict has an unknown action or invalid keys.
        KeyError: If a change references a path that doesn't exist in source.
    """
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(
            f"{output_path} already exists; enable overwrite to replace."
        )

    shutil.copy2(source_path, output_path)

    with h5py.File(output_path, "r+") as f:
        for i, change in enumerate(changes):
            action = change.get("action")
            if action == "rename":
                new_name = change.get("new_name")
                path = change.get("path")
                if not new_name or not path:
                    raise ValueError(
                        f"Change #{i} (rename) missing 'path' or 'new_name'"
                    )
                rename_node(f, path, new_name)
            elif action == "delete":
                path = change.get("path")
                if not path:
                    raise ValueError(f"Change #{i} (delete) missing 'path'")
                delete_node(f, path)
            else:
                raise ValueError(f"Change #{i} has unknown action: {action!r}")
