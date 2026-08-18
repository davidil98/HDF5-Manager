"""HDF5 file mutation operations: rename, delete, copy, move, merge."""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import ExitStack
from typing import Any

import h5py

from hdf5_manager.core.merge import order_merge_plan


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


def default_merge_output_path(destination_path: str) -> str:
    """Return a default output path with ``-merged`` before the extension."""
    base, ext = os.path.splitext(destination_path)
    return f"{base}-merged{ext}"


def apply_merges(
    merges: list[dict[str, Any]],
    output_path: str,
    overwrite: bool = False,
) -> None:
    """Apply a batch of cross-file group copies atomically.

    Each merge record must contain ``source_file``, ``source_path``,
    ``dest_file`` and ``dest_parent``. All records must use the same
    destination file because one output file is produced. The destination is
    copied to a temporary file, all merges are applied there, and the output
    is replaced only after success.

    Source and destination files are never modified unless *output_path* is
    explicitly the destination path with ``overwrite=True``. The source is
    always protected from being used as the output.
    """
    if not merges:
        raise ValueError("At least one merge is required")
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(
            f"{output_path} already exists; pass overwrite=True to replace."
        )

    required = ("source_file", "source_path", "dest_file", "dest_parent")
    destination_files = set()
    for i, merge in enumerate(merges):
        missing = [key for key in required if not merge.get(key)]
        if missing:
            raise ValueError(f"Merge #{i} is missing: {', '.join(missing)}")
        destination_files.add(os.path.abspath(merge["dest_file"]))
        if not os.path.isfile(merge["source_file"]):
            raise FileNotFoundError(merge["source_file"])
        if not os.path.isfile(merge["dest_file"]):
            raise FileNotFoundError(merge["dest_file"])
        if os.path.abspath(merge["source_file"]) == os.path.abspath(merge["dest_file"]):
            raise ValueError("Source and destination must be different files")
        if os.path.abspath(output_path) == os.path.abspath(merge["source_file"]):
            raise ValueError("Output cannot replace a source file")

    if len(destination_files) != 1:
        raise ValueError("All merges must use the same destination file")
    destination_path = next(iter(destination_files))

    # Validate source files before creating any output. Destination validation
    # happens again against the evolving temporary file below because a merge
    # may create the parent group of a later merge.
    with h5py.File(destination_path, "r") as destination:
        for merge in merges:
            with h5py.File(merge["source_file"], "r") as source:
                source_path = merge["source_path"]
                if source_path not in source:
                    raise KeyError(source_path)
                if not isinstance(source[source_path], h5py.Group):
                    raise ValueError(f"Only groups can be merged: {source_path}")

        existing_paths: set[str] = {"/"}
        existing_groups: set[str] = {"/"}

        def _collect_path(_name: str, item: h5py.Dataset | h5py.Group) -> None:
            existing_paths.add(item.name)
            if isinstance(item, h5py.Group):
                existing_groups.add(item.name)

        destination.visititems(_collect_path)
        ordered_merges = order_merge_plan(
            merges,
            existing_paths,
            existing_groups,
        )

    output_dir = os.path.dirname(os.path.abspath(output_path)) or "."
    fd, temp_path = tempfile.mkstemp(
        prefix=".hdf5_merge_",
        suffix=".h5.tmp",
        dir=output_dir,
    )
    os.close(fd)

    try:
        shutil.copy2(destination_path, temp_path)
        with h5py.File(temp_path, "r+") as destination, ExitStack() as stack:
            sources: dict[str, h5py.File] = {}
            for merge in ordered_merges:
                source_file = os.path.abspath(merge["source_file"])
                if source_file not in sources:
                    sources[source_file] = stack.enter_context(
                        h5py.File(source_file, "r")
                    )
                dest_parent = merge["dest_parent"]
                if dest_parent not in destination:
                    raise KeyError(dest_parent)
                if not isinstance(destination[dest_parent], h5py.Group):
                    raise ValueError(f"Destination is not a group: {dest_parent}")
                name = merge["name"]
                if name in destination[dest_parent]:
                    raise ValueError(f"'{name}' already exists in '{dest_parent}'")
                merge_files(
                    sources[source_file],
                    merge["source_path"],
                    destination,
                    dest_parent,
                    name,
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
