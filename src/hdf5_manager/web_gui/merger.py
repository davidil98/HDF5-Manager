"""Merger tab: preview and queue HDF5 group copies with Trello-style cards."""

from __future__ import annotations

import os
from typing import Any

import h5py
from nicegui import app, ui

from hdf5_manager.core.merge import apply_virtual_merges
from hdf5_manager.core.operations import (
    apply_merges,
    default_merge_output_path,
)
from hdf5_manager.core.tree import build_tree


@ui.refreshable
def create_merger_tab() -> None:
    """Build the Merger tab and its stable card-based layout."""
    _ensure_state()
    _build_file_controls()

    source_path = app.storage.user.get("h5_path")
    destination_path = app.storage.user.get("merger_dest_path")
    if (
        not source_path
        or source_path == "No file selected"
        or not destination_path
    ):
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
> Select a destination group, then click **+ Add** on any source group or
> subgroup to queue it for copying.
>
> Click **Root** to select the destination root. Queued copies appear in the
> destination preview until you click **Apply**.
    """.strip()
    ).classes(
        "w-full mx-4 mb-2 border-primary "
        "bg-blue-1 px-4 py-3 text-sm shadow-1"
    )
    with ui.row().classes("w-full items-stretch gap-4 p-4 flex-wrap"):
        with ui.column().classes("grow min-w-[320px] max-w-[50%]"):
            _build_source_board()
        with ui.column().classes("grow min-w-[320px] max-w-[50%]"):
            _build_destination_board()

    _build_pending_panel()
    _build_output_panel()
    _build_action_buttons()


def _ensure_state() -> None:
    """Initialize merger-specific session state without overwriting it."""
    defaults: dict[str, Any] = {
        "merger_dest_path": None,
        "merger_dest_parent": "/",
        "merger_selected_source": None,
        "merger_output_path": None,
        "pending_merges": [],
    }
    for key, value in defaults.items():
        if key not in app.storage.user:
            app.storage.user[key] = value


@ui.refreshable
def _build_file_controls() -> None:
    """Render global source, destination file, and target group controls."""
    source = app.storage.user.get("h5_path") or "No file selected"
    with ui.row().classes("w-full items-end gap-3 px-4 pt-3 flex-wrap"):
        with ui.column().classes("grow min-w-[280px]"):
            ui.label("Actual source file").classes("font-bold")
            ui.label(source).classes("text-grey text-sm").style(
                "word-break: break-all; white-space: normal;"
            )
        ui.label("->").classes("text-h6 text-grey pb-2")
        _build_destination_selector()


def _build_destination_selector() -> None:
    """Render destination file and the currently selected target group."""
    selected = app.storage.user.get("merger_dest_parent") or "/"
    with ui.column().classes("grow min-w-[280px]"):
        ui.label("Destination file").classes("font-bold")
        with ui.row().classes("w-full items-center"):
            ui.input().bind_value(
                app.storage.user, "merger_dest_path"
            ).classes("grow").props("readonly")
            ui.button(icon="folder_open", on_click=_pick_destination).props("flat")


@ui.refreshable
def _build_source_board() -> None:
    """Render all source groups as cards, including draggable-depth controls."""
    source_path = app.storage.user.get("h5_path")
    selected = app.storage.user.get("merger_selected_source")
    ui.label("Source groups").classes("text-subtitle1")
    ui.label(f"Selected source group: {selected or '(none)'}").classes(
        "text-caption"
    )
    with ui.column().classes(
        "w-full min-h-[100px] gap-2 p-2 bg-grey-2 rounded"
    ):
        if not source_path or not os.path.isfile(source_path):
            ui.label("(no source file selected)").classes("text-grey text-sm p-2")
            return
        try:
            with h5py.File(source_path, "r") as source:
                source_tree = build_tree(source)
        except OSError as error:
            ui.label(f"Could not read source: {error}").classes(
                "text-negative text-sm p-2"
            )
            return
        groups = [node for node in source_tree if node.get("type") == "group"]
        if not groups:
            ui.label("(source has no groups)").classes("text-grey text-sm p-2")
            return
        for node in groups:
            _render_source_group_card(node)


def _render_source_group_card(node: dict[str, Any]) -> None:
    """Render a source group card recursively with an Add action."""
    selected = node.get("id") == app.storage.user.get("merger_selected_source")
    card_classes = "w-full bg-white"
    if selected:
        card_classes += " border-2 border-primary"
    with ui.card().classes(card_classes):
        with ui.row().classes("w-full items-center gap-2 cursor-pointer").on(
            "click", lambda path=node["id"]: _on_source_select(path)
        ):
            ui.icon("folder").classes("text-amber")
            ui.label(node["label"]).classes("font-bold grow")
            ui.button(
                "Add",
                icon="add",
                on_click=lambda path=node["id"]: _queue_merge(path),
            ).props("dense color=primary")
        with ui.column().classes("w-full gap-1 pl-5"):
            for child in node.get("children", []):
                if child.get("type") == "group":
                    _render_source_group_card(child)
                else:
                    _render_dataset_row(child)


@ui.refreshable
def _build_destination_board() -> None:
    """Render the destination tree with virtual pending copies."""
    destination_path = str(app.storage.user.get("merger_dest_path") or "")
    source_path = str(app.storage.user.get("h5_path") or "")
    selected = app.storage.user.get("merger_dest_parent") or "/"
    with ui.row().classes("w-full items-center gap-4"):
        ui.label("Destination preview").classes("text-subtitle1")
        ui.button("Root", on_click=lambda: _on_destination_select("/")).props(
            "flat dense"
        )
    ui.label(f"Selected destination group: {selected}").classes("text-caption")
    with ui.column().classes(
        "w-full min-h-[100px] gap-2 p-2 bg-grey-2 rounded"
    ):
        if not destination_path or not os.path.isfile(destination_path):
            ui.label("(no destination file selected)").classes(
                "text-grey text-sm p-2"
            )
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
        groups = [node for node in virtual_tree if node.get("type") == "group"]
        if not groups:
            ui.label("(destination has no groups)").classes(
                "text-grey text-sm p-2"
            )
            return
        for node in groups:
            _render_destination_group_card(node)


def _render_destination_group_card(node: dict[str, Any]) -> None:
    """Render an existing or pending destination group recursively."""
    pending = bool(node.get("pending"))
    selected = node.get("id") == app.storage.user.get("merger_dest_parent")
    card_classes = "w-full bg-white"
    if pending:
        card_classes += " border-2 border-primary"
    if selected:
        card_classes += " ring-2 ring-primary"
    with ui.card().classes(card_classes):
        with ui.row().classes("w-full items-center gap-2 cursor-pointer").on(
            "click", lambda path=node["id"]: _on_destination_select(path)
        ):
            ui.icon("folder").classes("text-amber")
            ui.label(node["label"]).classes("font-bold grow")
            if pending:
                ui.badge("pending", color="primary")
                ui.button(
                    icon="close",
                ).on(
                    "click.stop",
                    lambda source_path=node.get(
                        "source_path", ""
                    ), dest_parent=node.get("dest_parent", "/"): _remove_merge_by_paths(
                        source_path, dest_parent
                    ),
                ).props("flat dense round color=negative")
        with ui.column().classes("w-full gap-1 pl-5"):
            for child in node.get("children", []):
                if child.get("type") == "group":
                    _render_destination_group_card(child)
                else:
                    _render_dataset_row(child)


def _render_dataset_row(node: dict[str, Any]) -> None:
    """Render a dataset as non-interactive group-card content."""
    with ui.row().classes("w-full items-center gap-2 px-2"):
        ui.icon("dataset", size="xs").classes("text-blue-grey")
        ui.label(node["label"]).classes("text-caption")
        shape = node.get("shape") or ""
        dtype = node.get("dtype") or ""
        if shape or dtype:
            ui.label(f"{shape} {dtype}").classes("text-caption text-grey")


def _on_source_select(source_path: str) -> None:
    """Store and display the source group selected by clicking its card."""
    app.storage.user["merger_selected_source"] = source_path
    _build_source_board.refresh()


def _on_destination_select(destination_path: str) -> None:
    """Store and display the destination group selected by clicking its card."""
    app.storage.user["merger_dest_parent"] = destination_path
    _build_file_controls.refresh()
    _build_destination_board.refresh()


@ui.refreshable
def _build_pending_panel() -> None:
    """Render pending operations and their remove buttons."""
    pending = app.storage.user.get("pending_merges", [])
    with ui.column().classes("w-full px-4 gap-1"):
        ui.label("Pending merges").classes("text-subtitle1")
        if not pending:
            ui.label("(none)").classes("text-grey text-sm")
            return
        for index, merge in enumerate(pending):
            with ui.row().classes("w-full items-center gap-2"):
                ui.icon("add").classes("text-grey")
                ui.label(
                    f"{merge.get('source_path')}  ->  "
                    f"{merge.get('dest_parent', '/') }"
                ).classes("text-caption grow")
                ui.button(
                    icon="close",
                    on_click=lambda i=index: _remove_merge(i),
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


def _queue_merge(source_path: str) -> None:
    """Validate and append one source group copy for the selected target."""
    source_file = app.storage.user.get("h5_path")
    destination_file = app.storage.user.get("merger_dest_path")
    dest_parent = app.storage.user.get("merger_dest_parent") or "/"
    if not source_file or not destination_file:
        ui.notify("Choose both files first", type="warning")
        return
    pending = list(app.storage.user.get("pending_merges", []))
    pending.append(
        {
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
        apply_virtual_merges(destination_tree, source_tree, pending)
    except (OSError, ValueError) as error:
        ui.notify(f"Merge not queued: {error}", type="negative")
        return
    app.storage.user["pending_merges"] = pending
    _build_destination_board.refresh()
    _build_pending_panel.refresh()
    ui.notify(f"Queued {source_path} -> {dest_parent}", type="positive")


def _remove_merge(index: int) -> None:
    """Remove one pending merge by its list position."""
    pending = list(app.storage.user.get("pending_merges", []))
    if 0 <= index < len(pending):
        merge = pending[index]
        _remove_merge_by_paths(
            str(merge.get("source_path") or ""),
            str(merge.get("dest_parent") or "/"),
        )


def _remove_merge_by_paths(source_path: str, dest_parent: str) -> None:
    """Remove a pending merge identified by its source and destination paths."""
    pending = list(app.storage.user.get("pending_merges", []))
    for index, merge in enumerate(pending):
        if (
            merge.get("source_path") == source_path
            and (merge.get("dest_parent") or "/") == dest_parent
        ):
            pending.pop(index)
            app.storage.user["pending_merges"] = pending
            removed_destination = _merge_destination_path(source_path, dest_parent)
            selected_destination = app.storage.user.get("merger_dest_parent") or "/"
            if selected_destination == removed_destination or selected_destination.startswith(
                f"{removed_destination}/"
            ):
                app.storage.user["merger_dest_parent"] = "/"
                _build_file_controls.refresh()
            _build_destination_board.refresh()
            _build_pending_panel.refresh()
            return


def _merge_destination_path(source_path: str, dest_parent: str) -> str:
    """Return the virtual path created by a pending group copy."""
    name = source_path.rstrip("/").rsplit("/", maxsplit=1)[-1]
    return f"/{name}" if dest_parent == "/" else f"{dest_parent}/{name}"


def _restore_merges() -> None:
    """Clear the virtual merge plan."""
    app.storage.user["pending_merges"] = []
    if not _destination_group_exists(
        app.storage.user.get("merger_dest_parent") or "/"
    ):
        app.storage.user["merger_dest_parent"] = "/"
        _build_file_controls.refresh()
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
    _build_destination_board.refresh()
    _build_pending_panel.refresh()
    ui.notify(f"Applied {len(pending)} merge(s) to {output}", type="positive")


async def _pick_destination() -> None:
    """Pick the destination file in native or browser mode."""
    from hdf5_manager.web_gui.general import LocalFilePicker

    if app.native.main_window:
        files = await app.native.main_window.create_file_dialog(
            allow_multiple=False,
            file_types=("HDF5 files (*.h5;*.hdf5)", "All files (*.*)"),
        )
    else:
        files = await LocalFilePicker(directory="~", multiple=False)
    if not files:
        return
    app.storage.user["merger_dest_path"] = files[0]
    app.storage.user["merger_dest_parent"] = "/"
    app.storage.user["pending_merges"] = []
    app.storage.user["merger_output_path"] = default_merge_output_path(files[0])
    create_merger_tab.refresh()


def _pick_output_path() -> None:
    """Open the output file picker without blocking NiceGUI's event loop."""
    from hdf5_manager.web_gui.general import LocalFilePicker

    async def _pick() -> None:
        if app.native.main_window:
            files = await app.native.main_window.create_file_dialog(
                allow_multiple=False,
                file_types=("HDF5 files (*.h5;*.hdf5)", "All files (*.*)"),
            )
        else:
            files = await LocalFilePicker(directory="~", multiple=False)
        if files:
            app.storage.user["merger_output_path"] = files[0]
            _build_output_panel.refresh()

    ui.timer(0.0, _pick, once=True)


def _read_merger_trees(
    source_path: str,
    destination_path: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read source and destination trees for queue validation."""
    with h5py.File(source_path, "r") as source:
        source_tree = build_tree(source)
    with h5py.File(destination_path, "r") as destination:
        destination_tree = build_tree(destination)
    return source_tree, destination_tree