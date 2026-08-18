"""Merger tab: preview and queue HDF5 group copies with tree controls."""

from __future__ import annotations

import os
import uuid
from typing import Any

import h5py
from nicegui import app, ui

from hdf5_manager.core.merge import (
    apply_virtual_merges,
    find_tree_node,
    minimal_group_selection,
    plan_virtual_merges,
)
from hdf5_manager.core.operations import (
    apply_merges,
    default_merge_output_path,
)
from hdf5_manager.core.tree import build_tree
from hdf5_manager.web_gui.general import pick_file, pick_save_file

_NO_FILE = "No file selected"


@ui.refreshable
def create_merger_tab() -> None:
    """Build the Merger tab and its tree-based layout."""
    _ensure_state()
    _build_file_controls()

    source_path = app.storage.user.get("h5_path")
    destination_path = app.storage.user.get("merger_dest_path")
    if not source_path or source_path == _NO_FILE or not destination_path:
        ui.label("Choose a source and destination HDF5 file to begin.").classes(
            "text-grey p-4"
        )
        return
    if os.path.abspath(source_path) == os.path.abspath(destination_path):
        ui.label("Source and destination must be different files.").classes(
            "text-negative p-4"
        )
        return
    if not os.path.isfile(source_path) or not os.path.isfile(destination_path):
        ui.label("One of the selected files no longer exists.").classes(
            "text-negative p-4"
        )
        return

    ui.markdown(
        """
> **Instructions**
>
> Tick one or more source groups, then select a destination group in the
> preview. Selecting a parent group includes its complete subtree.
>
> Pending copies are shown in the virtual destination tree until you click
> **Apply**.
        """.strip()
    ).classes(
        "w-full mx-4 mb-2 border-primary "
        "bg-blue-1 px-4 py-3 text-sm shadow-1"
    )

    with ui.row().classes("w-full items-stretch gap-4 p-4 flex-wrap"):
        with ui.column().classes("grow min-w-[320px] max-w-[50%]"):
            _build_source_panel()
        with ui.column().classes("grow min-w-[320px] max-w-[50%]"):
            _build_destination_board()

    _build_pending_panel()
    _build_output_panel()
    _build_action_buttons()


def _ensure_state() -> None:
    """Initialize merger state without overwriting the current plan."""
    defaults: dict[str, Any] = {
        "merger_dest_path": None,
        "merger_dest_parent": "/",
        "merger_selected_groups": [],
        "merger_output_path": None,
        "pending_merges": [],
        "merger_available_source_groups": [],
    }
    for key, value in defaults.items():
        if key not in app.storage.user:
            app.storage.user[key] = value


@ui.refreshable
def _build_file_controls() -> None:
    """Render source, destination, and the selected destination group."""
    source = app.storage.user.get("h5_path") or _NO_FILE
    selected = app.storage.user.get("merger_dest_parent") or "/"
    with ui.row().classes("w-full items-end gap-3 px-4 pt-3 flex-wrap"):
        with ui.column().classes("grow min-w-[280px]"):
            ui.label("Source file").classes("font-bold")
            ui.label(source).classes("text-grey text-sm").style(
                "word-break: break-all; white-space: normal;"
            )
        ui.label("->").classes("text-h6 text-grey pb-2")
        with ui.column().classes("grow min-w-[280px]"):
            ui.label("Destination file").classes("font-bold")
            with ui.row().classes("w-full items-center"):
                ui.input().bind_value(
                    app.storage.user, "merger_dest_path"
                ).classes("grow").props("readonly")
                ui.button(icon="folder_open", on_click=_pick_destination).props("flat")
            ui.label(f"Selected destination group: {selected}").classes(
                "text-caption"
            )


@ui.refreshable
def _build_source_panel() -> None:
    """Render a QTree with ticks enabled only for source groups."""
    source_path = app.storage.user.get("h5_path")
    selected = list(app.storage.user.get("merger_selected_groups", []))

    with ui.row().classes("w-full items-center justify-between"):
        ui.label("Source groups").classes("text-subtitle1")
        if selected:
            ui.label(f"{len(selected)} group(s) selected").classes(
                "text-caption text-primary font-bold"
            )
    with ui.row().classes("w-full items-center gap-2 mb-2 flex-wrap"):
        ui.button(
            "Queue selected",
            icon="add",
            on_click=_queue_selected_merges,
        ).props("dense color=primary")
        ui.button("Select root groups", icon="select_all", on_click=_select_all_sources).props(
            "flat dense"
        )
        ui.button("Clear", icon="clear_all", on_click=_clear_sources).props(
            "flat dense"
        )

    if not source_path or source_path == _NO_FILE or not os.path.isfile(source_path):
        ui.label("(no source file selected)").classes("text-grey text-sm p-2")
        return

    try:
        with h5py.File(source_path, "r") as source:
            tree_data = build_tree(source)
    except OSError as error:
        ui.label(f"Could not read source: {error}").classes(
            "text-negative text-sm p-2"
        )
        return

    group_paths = _prepare_source_tree(tree_data)
    app.storage.user["merger_available_source_groups"] = group_paths
    selected = [path for path in selected if path in group_paths]
    selected = minimal_group_selection(selected)
    app.storage.user["merger_selected_groups"] = selected

    if not group_paths:
        ui.label("(source has no groups)").classes("text-grey text-sm p-2")
        return

    tree = ui.tree(
        tree_data,
        label_key="label",
        node_key="id",
        tick_strategy="strict",
        on_tick=_on_source_tick,
    ).classes("w-full max-h-[520px] overflow-auto")
    if selected:
        tree.tick(selected)

    if selected:
        with ui.row().classes("w-full gap-1 flex-wrap mt-2"):
            for path in selected:
                ui.chip(
                    path,
                    icon="folder",
                    removable=True,
                    on_value_change=lambda _event, group_path=path: _remove_source_selection(
                        group_path
                    ),
                )


def _prepare_source_tree(nodes: list[dict[str, Any]]) -> list[str]:
    """Hide dataset ticks and return every selectable group path."""
    groups: list[str] = []
    for node in nodes:
        if node.get("type") == "group":
            groups.append(node["id"])
            groups.extend(_prepare_source_tree(node.get("children", [])))
        else:
            node["tickStrategy"] = "none"
    return groups


def _on_source_tick(event: Any) -> None:
    """Store only group paths and remove redundant descendant selections."""
    available = set(app.storage.user.get("merger_available_source_groups", []))
    ticked = [path for path in (event.value or []) if path in available]
    app.storage.user["merger_selected_groups"] = minimal_group_selection(ticked)
    _build_source_panel.refresh()


def _select_all_sources() -> None:
    """Select root-level source groups so their subtrees remain intact."""
    source_path = app.storage.user.get("h5_path")
    if not source_path or not os.path.isfile(source_path):
        return
    with h5py.File(source_path, "r") as source:
        tree_data = build_tree(source)
    app.storage.user["merger_selected_groups"] = [
        node["id"] for node in tree_data if node.get("type") == "group"
    ]
    _build_source_panel.refresh()


def _clear_sources() -> None:
    """Clear all selected source groups."""
    app.storage.user["merger_selected_groups"] = []
    _build_source_panel.refresh()


def _remove_source_selection(group_path: str) -> None:
    """Remove one source group from the current selection."""
    selected = [
        path
        for path in app.storage.user.get("merger_selected_groups", [])
        if path != group_path
    ]
    app.storage.user["merger_selected_groups"] = selected
    _build_source_panel.refresh()


@ui.refreshable
def _build_destination_board() -> None:
    """Render the physical destination plus all pending virtual copies."""
    destination_path = str(app.storage.user.get("merger_dest_path") or "")
    source_path = str(app.storage.user.get("h5_path") or "")
    selected = app.storage.user.get("merger_dest_parent") or "/"

    with ui.row().classes("w-full items-center gap-4"):
        ui.label("Destination preview").classes("text-subtitle1")
        ui.button("Root", on_click=lambda: _on_destination_select("/")).props(
            "flat dense"
        )
    ui.label(f"Selected destination group: {selected}").classes("text-caption")

    if (
        not source_path
        or source_path == _NO_FILE
        or not os.path.isfile(source_path)
        or not destination_path
        or not os.path.isfile(destination_path)
    ):
        ui.label("(no destination file selected)").classes("text-grey text-sm p-2")
        return

    try:
        source_tree, destination_tree = _read_merger_trees(
            source_path, destination_path
        )
        virtual_tree = apply_virtual_merges(
            destination_tree,
            source_tree,
            app.storage.user.get("pending_merges", []),
        )
    except (OSError, ValueError) as error:
        ui.label(f"Could not build destination preview: {error}").classes(
            "text-negative text-sm p-2"
        )
        return

    ui.tree(
        virtual_tree,
        label_key="label",
        node_key="id",
        on_select=_on_destination_tree_select,
    ).classes("w-full max-h-[520px] overflow-auto")
    if selected != "/" and find_tree_node(virtual_tree, selected) is None:
        app.storage.user["merger_dest_parent"] = "/"
        _build_file_controls.refresh()
    if not virtual_tree:
        ui.label("(destination has no nodes)").classes("text-grey text-sm p-2")


def _on_destination_tree_select(event: Any) -> None:
    """Select a group from the physical or virtual destination tree."""
    path = event.value
    if not isinstance(path, str):
        return
    if path == "/":
        _on_destination_select(path)
        return

    source_path = app.storage.user.get("h5_path")
    destination_path_value = app.storage.user.get("merger_dest_path")
    if not source_path or not destination_path_value:
        return
    try:
        source_tree, destination_tree = _read_merger_trees(
            source_path, destination_path_value
        )
        virtual_tree = apply_virtual_merges(
            destination_tree,
            source_tree,
            app.storage.user.get("pending_merges", []),
        )
    except (OSError, ValueError):
        return
    node = find_tree_node(virtual_tree, path)
    if node is not None and node.get("type") == "group":
        _on_destination_select(path)


def _on_destination_select(destination_path: str) -> None:
    """Store and display the selected destination group."""
    app.storage.user["merger_dest_parent"] = destination_path
    _build_file_controls.refresh()
    _build_destination_board.refresh()


@ui.refreshable
def _build_pending_panel() -> None:
    """Render normalized pending operations and their remove buttons."""
    pending = app.storage.user.get("pending_merges", [])
    with ui.column().classes("w-full px-4 gap-1"):
        ui.label("Pending merges").classes("text-subtitle1")
        if not pending:
            ui.label("(none)").classes("text-grey text-sm")
            return
        for index, merge in enumerate(pending):
            destination = merge.get("destination_path") or _merge_destination_path(
                str(merge.get("source_path") or ""),
                str(merge.get("dest_parent") or "/"),
                merge.get("name"),
            )
            with ui.row().classes("w-full items-center gap-2"):
                ui.icon("add").classes("text-grey")
                ui.label(f"{merge.get('source_path')}  ->  {destination}").classes(
                    "text-caption grow"
                )
                ui.button(
                    icon="close",
                    on_click=lambda operation_index=index: _remove_merge(
                        operation_index
                    ),
                ).props("flat dense round color=negative")


@ui.refreshable
def _build_output_panel() -> None:
    """Render the output path used by Apply."""
    destination = app.storage.user.get("merger_dest_path") or ""
    if not app.storage.user.get("merger_output_path") and destination:
        app.storage.user["merger_output_path"] = default_merge_output_path(destination)
    with ui.column().classes("w-full px-4 pt-3"):
        ui.label("Output file").classes("font-bold")
        with ui.row().classes("w-full items-center"):
            ui.input().bind_value(
                app.storage.user, "merger_output_path"
            ).classes("grow")
            ui.button(icon="folder_open", on_click=_pick_output_path).props("flat")
        ui.label(
            "The selected source and destination files remain unchanged by default."
        ).classes("text-caption text-grey")


@ui.refreshable
def _build_action_buttons() -> None:
    """Render Restore and Apply controls."""
    with ui.row().classes("w-full justify-end gap-2 px-4 py-4"):
        ui.button("Restore", icon="restore", on_click=_restore_merges).props("outline")
        ui.button("Apply", icon="save", on_click=_apply_merges).props("color=primary")


def _queue_selected_merges() -> None:
    """Queue selected source groups using the normalized virtual plan."""
    selected = minimal_group_selection(
        list(app.storage.user.get("merger_selected_groups", []))
    )
    if not selected:
        ui.notify("Select one or more source groups first.", type="warning")
        return

    source_file = app.storage.user.get("h5_path")
    destination_file = app.storage.user.get("merger_dest_path")
    dest_parent = app.storage.user.get("merger_dest_parent") or "/"
    if not source_file or not destination_file:
        ui.notify("Choose both files first", type="warning")
        return
    if os.path.abspath(source_file) == os.path.abspath(destination_file):
        ui.notify("Source and destination must be different files.", type="negative")
        return

    pending = list(app.storage.user.get("pending_merges", []))
    before_count = len(pending)
    for source_path in selected:
        if any(
            merge.get("source_path") == source_path
            and (merge.get("dest_parent") or "/") == dest_parent
            for merge in pending
        ):
            continue
        pending.append(
            {
                "id": uuid.uuid4().hex,
                "source_file": source_file,
                "source_path": source_path,
                "dest_file": destination_file,
                "dest_parent": dest_parent,
            }
        )

    try:
        source_tree, destination_tree = _read_merger_trees(
            source_file, destination_file
        )
        _, normalized_pending = plan_virtual_merges(
            destination_tree,
            source_tree,
            pending,
        )
    except (OSError, ValueError) as error:
        ui.notify(f"Merge not queued: {error}", type="negative")
        return

    app.storage.user["pending_merges"] = normalized_pending
    app.storage.user["merger_selected_groups"] = []
    _build_source_panel.refresh()
    _build_destination_board.refresh()
    _build_pending_panel.refresh()
    ui.notify(
        f"Queued {len(normalized_pending) - before_count} item(s) -> {dest_parent}",
        type="positive",
    )


def _remove_merge(index: int) -> None:
    """Remove one pending merge and all operations nested below it."""
    pending = list(app.storage.user.get("pending_merges", []))
    if 0 <= index < len(pending):
        _remove_merge_by_id(pending[index].get("id"), index)


def _remove_merge_by_id(operation_id: Any, fallback_index: int | None = None) -> None:
    """Remove a merge by ID and cascade to its virtual descendants."""
    pending = list(app.storage.user.get("pending_merges", []))
    index = next(
        (
            i
            for i, merge in enumerate(pending)
            if operation_id is not None and merge.get("id") == operation_id
        ),
        fallback_index if fallback_index is not None else -1,
    )
    if index < 0 or index >= len(pending):
        return

    removed = pending[index]
    removed_path = removed.get("destination_path") or _merge_destination_path(
        str(removed.get("source_path") or ""),
        str(removed.get("dest_parent") or "/"),
        removed.get("name"),
    )
    remaining = [
        merge
        for merge in pending
        if merge is not removed
        and not (
            (merge.get("dest_parent") or "/") == removed_path
            or str(merge.get("dest_parent") or "/").startswith(
                f"{removed_path}/"
            )
        )
    ]
    app.storage.user["pending_merges"] = remaining
    selected = app.storage.user.get("merger_dest_parent") or "/"
    if selected == removed_path or selected.startswith(f"{removed_path}/"):
        app.storage.user["merger_dest_parent"] = "/"
        _build_file_controls.refresh()
    _build_destination_board.refresh()
    _build_pending_panel.refresh()


def _merge_destination_path(
    source_path: str,
    dest_parent: str,
    name: str | None = None,
) -> str:
    """Return the virtual path created by a pending group copy."""
    group_name = name or source_path.rstrip("/").rsplit("/", maxsplit=1)[-1]
    return f"/{group_name}" if dest_parent == "/" else f"{dest_parent}/{group_name}"


def _restore_merges() -> None:
    """Clear the virtual merge plan."""
    app.storage.user["pending_merges"] = []
    app.storage.user["merger_selected_groups"] = []
    if not _destination_group_exists(
        app.storage.user.get("merger_dest_parent") or "/"
    ):
        app.storage.user["merger_dest_parent"] = "/"
        _build_file_controls.refresh()
    _build_source_panel.refresh()
    _build_destination_board.refresh()
    _build_pending_panel.refresh()
    ui.notify("Pending merges cleared")


def _destination_group_exists(path: str) -> bool:
    """Return whether *path* is an actual group in the destination file."""
    if path == "/":
        return True
    destination_file = app.storage.user.get("merger_dest_path")
    if not destination_file or not os.path.isfile(destination_file):
        return False
    try:
        with h5py.File(destination_file, "r") as destination:
            return path in destination and isinstance(destination[path], h5py.Group)
    except OSError:
        return False


def _apply_merges() -> None:
    """Apply the pending merge plan after output confirmation."""
    pending = app.storage.user.get("pending_merges", [])
    source = app.storage.user.get("h5_path")
    destination = app.storage.user.get("merger_dest_path")
    output = (app.storage.user.get("merger_output_path") or "").strip()
    if not pending:
        ui.notify("No pending merges", type="warning")
        return
    if not source or not destination:
        ui.notify("Choose both files first", type="negative")
        return
    if not output:
        output = default_merge_output_path(destination)
        app.storage.user["merger_output_path"] = output
    if os.path.abspath(output) == os.path.abspath(source):
        ui.notify("Output cannot replace the source file", type="negative")
        return
    if os.path.exists(output):
        _confirm_apply(output, pending)
    else:
        _do_apply(output, pending)


def _confirm_apply(output: str, pending: list[dict[str, Any]]) -> None:
    """Confirm replacement of an existing merge output."""
    with ui.dialog() as dialog, ui.card():
        ui.label("Output file already exists").classes("text-h6")
        ui.label(
            f"Replace '{os.path.basename(output)}' with "
            f"{len(pending)} pending merge(s)?"
        ).classes("text-grey")
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("outline")
            ui.button(
                "Overwrite",
                on_click=lambda: _confirm_and_apply(dialog, output, pending),
                color="negative",
            )
    dialog.open()


def _confirm_and_apply(
    dialog: ui.dialog,
    output: str,
    pending: list[dict[str, Any]],
) -> None:
    """Close the confirmation dialog and run the merge batch."""
    dialog.close()
    _do_apply(output, pending)


def _do_apply(output: str, pending: list[dict[str, Any]]) -> None:
    """Apply the plan and clear it only after success."""
    try:
        apply_merges(pending, output, overwrite=True)
    except (FileExistsError, FileNotFoundError, KeyError, OSError, ValueError) as error:
        ui.notify(f"Apply failed: {error}", type="negative")
        return
    app.storage.user["pending_merges"] = []
    app.storage.user["merger_selected_groups"] = []
    _build_source_panel.refresh()
    _build_destination_board.refresh()
    _build_pending_panel.refresh()
    ui.notify(f"Applied {len(pending)} merge(s) to {output}", type="positive")


async def _pick_destination() -> None:
    """Pick the destination file with the shared native/web picker."""
    files = await pick_file(
        directory="~",
        multiple=False,
        file_types=("HDF5 files (*.h5;*.hdf5)", "All files (*.*)"),
        extensions=(".h5", ".hdf5"),
    )
    if not files:
        return
    app.storage.user["merger_dest_path"] = files[0]
    app.storage.user["merger_dest_parent"] = "/"
    app.storage.user["pending_merges"] = []
    app.storage.user["merger_selected_groups"] = []
    app.storage.user["merger_output_path"] = default_merge_output_path(files[0])
    create_merger_tab.refresh()


def _pick_output_path() -> None:
    """Open the shared save dialog without blocking NiceGUI's event loop."""

    async def _pick() -> None:
        output = app.storage.user.get("merger_output_path") or ""
        files = await pick_save_file(
            path=output,
            save_filename=os.path.basename(output),
            file_types=("HDF5 files (*.h5;*.hdf5)", "All files (*.*)"),
            extensions=(".h5", ".hdf5"),
        )
        if files:
            app.storage.user["merger_output_path"] = files[0]
            _build_output_panel.refresh()

    ui.timer(0.0, _pick, once=True)


def _read_merger_trees(
    source_path: str,
    destination_path: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read source and destination trees for queue validation and preview."""
    with h5py.File(source_path, "r") as source:
        source_tree = build_tree(source)
    with h5py.File(destination_path, "r") as destination:
        destination_tree = build_tree(destination)
    return source_tree, destination_tree
