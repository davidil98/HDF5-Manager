"""HDF5 file mutation operations: rename, delete, copy, move, merge."""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import Any

import h5py


def default_output_path(source_path: str) -> str:
    """Return a default output path with ``-edit`` before the extension.

    Examples:
        ``/data/foo.h5``   → ``/data/foo-edit.h5``
        ``/data/foo.hdf5`` → ``/data/foo-edit.hdf5``
        ``/data/foo``      → ``/data/foo-edit``
        ``foo.h5``         → ``foo-edit.h5``
    """
    base, ext = os.path.splitext(source_path)
    return f"{base}-edit{ext}"


def rename_node(h5file: h5py.File, path: str, new_name: str) -> None:
    """Rename a group or dataset within the same parent.

    Args:
        h5file: An open h5py File (mode ``r+`` or ``a``).
        path: Absolute HDF5 path to the node to rename.
        new_name: New basename for the node.

    Raises:
        ValueError: If *path* is the root group, or if *new_name* is
            already used by another entry in the same parent.
    """
    if path == "/":
        raise ValueError("Cannot rename the root group")
    parent_path, old_name = os.path.split(path)
    parent = h5file[parent_path]
    if new_name in parent and new_name != old_name:
        raise ValueError(
            f"'{new_name}' already exists in '{parent_path}'; cannot rename"
        )
    parent.move(path, new_name)


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
    """Apply a batch of pending changes from *source_path* to *output_path*.

    Safe workflow:

        1. Refuse if *output_path* exists and *overwrite* is False.
        2. Create a temp file alongside *output_path*.
        3. Copy *source_path* to the temp file and apply every change on it.
        4. Atomically replace *output_path* with the temp.
        5. On any failure, the temp file is removed and *output_path* is
           left untouched.

    Using a temp file makes the operation safe even when
    ``output_path == source_path``: the source is replaced only after all
    mutations succeed, never partially.

    Args:
        source_path: Path to the source HDF5 file.
        changes: List of change dicts. Each must contain:

            - ``{"action": "rename", "path": str, "new_name": str}``
            - ``{"action": "delete", "path": str}``

        output_path: Destination path. Created (or replaced) by the function.
        overwrite: If True, replace an existing *output_path*.

    Raises:
        FileExistsError: If *output_path* exists and *overwrite* is False.
        ValueError: If a change dict has an unknown action or invalid keys.
        KeyError: If a change references a path that doesn't exist in source.
        OSError: On filesystem errors during copy or atomic replace.
    """
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(
            f"{output_path} already exists; pass overwrite=True to replace."
        )

    output_dir = os.path.dirname(os.path.abspath(output_path)) or "."
    fd, temp_path = tempfile.mkstemp(
        prefix=".hdf5_apply_",
        suffix=".h5.tmp",
        dir=output_dir,
    )
    os.close(fd)

    try:
        shutil.copy2(source_path, temp_path)

        with h5py.File(temp_path, "r+") as f:
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
                        raise ValueError(
                            f"Change #{i} (delete) missing 'path'"
                        )
                    delete_node(f, path)
                else:
                    raise ValueError(
                        f"Change #{i} has unknown action: {action!r}"
                    )

        try:
            os.replace(temp_path, output_path)
        except OSError:
            shutil.move(temp_path, output_path)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise
