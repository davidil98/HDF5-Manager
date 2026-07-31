"""HDF5 file mutation operations: rename, delete, copy, move, merge."""

from __future__ import annotations

import os

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
