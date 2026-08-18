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


def minimal_group_selection(paths: list[str]) -> list[str]:
    """Remove selected descendants covered by an already selected ancestor."""
    normalized = sorted(
        {normalize_hdf5_path(path) for path in paths},
        key=lambda path: (path.count("/"), path),
    )
    result: list[str] = []
    for path in normalized:
        if not any(
            path == parent or path.startswith(f"{parent}/") for parent in result
        ):
            result.append(path)
    return result


def destination_path(dest_parent: str, name: str) -> str:
    """Return the absolute path for *name* below *dest_parent*."""
    dest_parent = normalize_hdf5_path(dest_parent)
    return f"/{name}" if dest_parent == "/" else f"{dest_parent}/{name}"


def _validate_name(name: Any) -> str:
    """Validate and return a single HDF5 destination component."""
    if not isinstance(name, str) or not name or "/" in name:
        raise ValueError(f"Invalid destination name: {name!r}")
    return name


def _unique_name(occupied: set[str], requested: str) -> str:
    """Return a deterministic non-conflicting merge name."""
    if requested not in occupied:
        return requested
    candidate = f"{requested}-merged"
    index = 2
    while candidate in occupied:
        candidate = f"{requested}-merged-{index}"
        index += 1
    return candidate


def _tree_paths(
    nodes: list[dict[str, Any]],
) -> tuple[set[str], set[str]]:
    """Collect all node paths and group paths from a tree representation."""
    all_paths: set[str] = set()
    group_paths: set[str] = {"/"}

    def _collect(current: list[dict[str, Any]]) -> None:
        for node in current:
            path = normalize_hdf5_path(node["id"])
            all_paths.add(path)
            if node.get("type") == "group":
                group_paths.add(path)
            _collect(node.get("children", []))

    _collect(nodes)
    return all_paths, group_paths


def _sibling_names(paths: set[str], parent: str) -> set[str]:
    """Return direct child names below *parent*."""
    prefix = "/" if parent == "/" else f"{parent}/"
    names: set[str] = set()
    for path in paths:
        if not path.startswith(prefix):
            continue
        remainder = path[len(prefix) :]
        if remainder and "/" not in remainder:
            names.add(remainder)
    return names


def order_merge_plan(
    merges: list[dict[str, Any]],
    existing_paths: set[str],
    existing_groups: set[str],
) -> list[dict[str, Any]]:
    """Normalize, name, and order merges against an evolving destination tree.

    A destination parent may be created by an earlier merge. The input order is
    retained whenever possible, while merges whose parents are virtual are
    delayed until those parents have been created.
    """
    paths = {normalize_hdf5_path(path) for path in existing_paths}
    groups = {normalize_hdf5_path(path) for path in existing_groups}
    remaining = list(merges)
    ordered: list[dict[str, Any]] = []

    while remaining:
        progress = False
        for index, merge in enumerate(remaining):
            dest_parent = normalize_hdf5_path(merge.get("dest_parent", "/"))
            if dest_parent not in groups:
                continue

            source_path = normalize_hdf5_path(merge.get("source_path", ""))
            requested = merge.get("name")
            if requested is None or requested == "":
                requested = source_path.rstrip("/").rsplit("/", maxsplit=1)[-1]
            name = _validate_name(requested)
            if "name" not in merge or not merge.get("name"):
                name = _unique_name(_sibling_names(paths, dest_parent), name)

            new_path = destination_path(dest_parent, name)
            if new_path in paths:
                raise ValueError(f"'{name}' already exists in '{dest_parent}'")

            normalized = dict(merge)
            normalized["source_path"] = source_path
            normalized["dest_parent"] = dest_parent
            normalized["name"] = name
            normalized["destination_path"] = new_path
            ordered.append(normalized)
            paths.add(new_path)
            groups.add(new_path)
            remaining.pop(index)
            progress = True
            break

        if not progress:
            unresolved = normalize_hdf5_path(
                remaining[0].get("dest_parent", "/")
            )
            raise ValueError(f"Destination group does not exist: {unresolved}")

    return ordered


def plan_virtual_merges(
    destination_tree: list[dict[str, Any]],
    source_tree: list[dict[str, Any]],
    merges: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build a virtual destination tree and its normalized merge plan."""
    virtual_tree = copy.deepcopy(destination_tree)
    all_paths, group_paths = _tree_paths(virtual_tree)
    ordered = order_merge_plan(merges, all_paths, group_paths)

    for merge in ordered:
        source_path = merge["source_path"]
        source_node = find_tree_node(source_tree, source_path)
        if source_node is None:
            raise ValueError(f"Source group does not exist: {source_path}")
        if source_node.get("type") != "group":
            raise ValueError(f"Only groups can be merged: {source_path}")

        dest_parent = merge["dest_parent"]
        destination_parent = (
            None if dest_parent == "/" else find_tree_node(virtual_tree, dest_parent)
        )
        children = (
            virtual_tree
            if destination_parent is None
            else destination_parent["children"]
        )
        destination_path_value = merge["destination_path"]
        copied = copy.deepcopy(source_node)
        _rebase_node(copied, source_path, destination_path_value)
        copied["pending"] = True
        copied["label"] = merge["name"]
        copied["source_path"] = source_path
        copied["dest_parent"] = dest_parent
        copied["name"] = merge["name"]
        copied["destination_path"] = destination_path_value
        if merge.get("id") is not None:
            copied["merge_id"] = merge["id"]
        children.append(copied)

    return virtual_tree, ordered


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
    virtual_tree, _ = plan_virtual_merges(destination_tree, source_tree, merges)
    return virtual_tree


def _rebase_node(node: dict[str, Any], old_path: str, new_path: str) -> None:
    """Replace an HDF5 path prefix in a copied tree node recursively."""
    node["id"] = new_path
    for child in node.get("children", []):
        child_old_path = child["id"]
        child_new_path = new_path + child_old_path[len(old_path) :]
        _rebase_node(child, old_path, child_new_path)
