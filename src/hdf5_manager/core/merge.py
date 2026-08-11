"""Pure helpers for planning and previewing HDF5 merge operations."""

from __future__ import annotations

import copy
import posixpath
from typing import Any


def normalize_hdf5_path(path: str) -> str:
    """Return *path* in canonical absolute HDF5 path form."""
    if not isinstance(path, str) or not path:
        raise ValueError("HDF5 paths must be non-empty strings")
    normalized = posixpath.normpath(path)
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def find_tree_node(nodes: list[dict[str, Any]], path: str) -> dict[str, Any] | None:
    """Return the node with the given HDF5 path from a tree representation."""
    path = normalize_hdf5_path(path)
    for node in nodes:
        if node.get("id") == path:
            return node
        children = node.get("children", [])
        found = find_tree_node(children, path) if children else None
        if found is not None:
            return found
    return None


def apply_virtual_merges(
    destination_tree: list[dict[str, Any]],
    source_tree: list[dict[str, Any]],
    merges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a destination tree with pending group copies applied in memory.

    The input trees are never modified. A merge record must contain
    ``source_path`` and ``dest_parent``. The source node is copied, its
    descendants are rebased to their virtual destination paths, and the copy
    is marked with ``pending=True`` for the UI.

    Raises:
        ValueError: If a source group, destination parent, or destination name
            is invalid or already exists.
    """
    virtual_tree = copy.deepcopy(destination_tree)
    occupied: set[tuple[str, str]] = set()

    for merge in merges:
        source_path = normalize_hdf5_path(merge.get("source_path", ""))
        dest_parent = normalize_hdf5_path(merge.get("dest_parent", "/"))
        source_node = find_tree_node(source_tree, source_path)
        if source_node is None:
            raise ValueError(f"Source group does not exist: {source_path}")
        if source_node.get("type") != "group":
            raise ValueError(f"Only groups can be merged: {source_path}")

        destination_parent = (
            None if dest_parent == "/" else find_tree_node(virtual_tree, dest_parent)
        )
        if dest_parent != "/" and destination_parent is None:
            raise ValueError(f"Destination group does not exist: {dest_parent}")
        if destination_parent is not None and destination_parent.get("type") != "group":
            raise ValueError(f"Destination is not a group: {dest_parent}")

        name = merge.get("name") or posixpath.basename(source_path)
        if not isinstance(name, str) or not name or "/" in name:
            raise ValueError(f"Invalid destination name: {name!r}")
        destination_path = f"/{name}" if dest_parent == "/" else f"{dest_parent}/{name}"
        key = (dest_parent, name)
        children = (
            virtual_tree
            if destination_parent is None
            else destination_parent["children"]
        )
        if key in occupied or any(child.get("label") == name for child in children):
            raise ValueError(f"'{name}' already exists in '{dest_parent}'")

        copied = copy.deepcopy(source_node)
        _rebase_node(copied, source_path, destination_path)
        copied["pending"] = True
        copied["source_path"] = source_path
        copied["dest_parent"] = dest_parent
        children.append(copied)
        occupied.add(key)

    return virtual_tree


def _rebase_node(node: dict[str, Any], old_path: str, new_path: str) -> None:
    """Replace an HDF5 path prefix in a copied tree node recursively."""
    node["id"] = new_path
    for child in node.get("children", []):
        child_old_path = child["id"]
        child_new_path = new_path + child_old_path[len(old_path) :]
        _rebase_node(child, old_path, child_new_path)
