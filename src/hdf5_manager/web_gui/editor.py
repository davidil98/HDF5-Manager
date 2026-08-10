"""Editor tab: rename/delete HDF5 groups and datasets with preview-before-apply.

Workflow:
    1. User opens a file in the Main Window.
    2. User switches to the Editor tab; the tree mirrors the source.
    3. User selects a node, types a new name, clicks "Rename Selected"
       (or "Delete Selected" + confirmation). The change is queued in
       ``app.storage.user["pending_changes"]`` (in-memory only).
    4. The tree re-renders to show a *virtual preview* of the queued
       changes (source + applied pending).
    5. User configures the output path (with optional "Reemplazar"
       overwrite flag) and clicks "Apply".
    6. ``apply_changes()`` copies the source to the output and applies
       all queued changes. The source file is never modified.
    7. "Restore" empties the pending list and re-renders the tree.
"""

from __future__ import annotations

import os
from typing import Any

import h5py
from nicegui import app, ui

from hdf5_manager.core.operations import apply_changes
from hdf5_manager.core.tree import build_tree

# ── Tree virtual helpers (pure functions on dict structure) ────────


def apply_virtual_changes(tree: list[dict], pending: list[dict]) -> list[dict]:
    """Return a deep copy of *tree* with *pending* applied in-memory.

    Deleted nodes are removed. Renamed nodes get their ``id`` and
    ``label`` updated. Children of renamed nodes are also updated
    recursively (their ids are absolute paths).
    """
    import copy

    new_tree = copy.deepcopy(tree)
    for change in pending:
        if change["action"] == "rename":
            _virtual_rename(new_tree, change["path"], change["new_name"])
        elif change["action"] == "delete":
            _virtual_delete(new_tree, change["path"])
    return new_tree


def _virtual_rename(nodes: list[dict], path: str, new_name: str) -> bool:
    """Recursively find node with id == path and rename it. Returns True
    if found."""
    for node in nodes:
        if node["id"] == path:
            parent = "/".join(path.split("/")[:-1])
            node["id"] = f"{parent}/{new_name}" if parent else f"/{new_name}"
            node["label"] = new_name
            return True
        if node.get("children"):
            if _virtual_rename(node["children"], path, new_name):
                # Update descendants' ids since their parent path changed.
                _virtual_rebase_children(node["children"], path, node["id"])
                return True
    return False


def _virtual_rebase_children(
    nodes: list[dict], old_parent: str, new_parent: str
) -> None:
    """Rewrite absolute paths in descendants after a parent rename."""
    for node in nodes:
        if node["id"].startswith(old_parent + "/"):
            node["id"] = new_parent + node["id"][len(old_parent) :]
        if node.get("children"):
            _virtual_rebase_children(node["children"], old_parent, new_parent)


def _virtual_delete(nodes: list[dict], path: str) -> bool:
    """Recursively remove node with id == path. Returns True if found."""
    for i, node in enumerate(nodes):
        if node["id"] == path:
            del nodes[i]
            return True
        if node.get("children"):
            if _virtual_delete(node["children"], path):
                return True
    return False


# ── Main layout ─────────────────────────────────────────────────────

@ui.refreshable
def create_editor_tab() -> None:
    """Build the Editor tab layout."""
    # Top: option to apply changes in a new file (replace semantics).
    apply_new = ui.checkbox("Apply changes in a new file").bind_value(
        app.storage.user, "apply_to_new_file"
    )

    with ui.splitter(limits=(250, 500)).classes("w-full flex-grow") as splitter:
        with splitter.before:
            _build_editor_tree_panel()
        with splitter.after:
            with ui.column().classes("w-full p-4 gap-2"):
                _build_selected_info()
                _build_rename_section()
                _build_delete_section()
                _build_pending_list()
                ui.separator()
                _build_output_section(apply_new)
                _build_apply_buttons()


# ── Panel builders ──────────────────────────────────────────────────


@ui.refreshable
def _build_editor_tree_panel() -> None:
    """Tree showing source file + virtual pending changes."""
    ui.label("Structure (preview)").classes("text-subtitle2 p-2 pb-0")
    path = app.storage.user.get("h5_path")
    if not path or not os.path.isfile(path):
        ui.label("(no file loaded)").classes("text-grey text-sm p-2")
        return
    with h5py.File(path, "r") as f:
        raw_tree = build_tree(f)
    pending = app.storage.user.get("pending_changes", [])
    tree_data = apply_virtual_changes(raw_tree, pending)
    ui.tree(
        tree_data,
        label_key="label",
        node_key="id",
        on_select=lambda e: _on_select(e),
    ).classes("w-full h-full overflow-auto")


@ui.refreshable
def _build_selected_info() -> None:
    """Show currently selected node."""
    ui.label("Selected:").classes("font-bold")
    node = app.storage.user.get("selected_node")
    ui.label(node or "(none)").classes("text-grey text-sm")


@ui.refreshable
def _build_rename_section() -> None:
    """Input + button to queue a rename."""
    new_name = ui.input(placeholder="Enter new name").classes("w-full")
    ui.button(
        "Rename Selected",
        on_click=lambda: _queue_rename(new_name.value),
    ).classes("w-full")


@ui.refreshable
def _build_delete_section() -> None:
    """Button to queue a delete (with confirmation dialog)."""
    ui.button(
        "Delete Selected",
        on_click=_confirm_queue_delete,
        color="negative",
    ).classes("w-full")


@ui.refreshable
def _build_pending_list() -> None:
    """Show queued changes as a scrollable list."""
    ui.label("Pending:").classes("font-bold pt-2")
    pending = app.storage.user.get("pending_changes", [])
    if not pending:
        ui.label("(no changes)").classes("text-grey text-sm")
        return
    with ui.column().classes("w-full gap-1"):
        for change in pending:
            if change["action"] == "rename":
                text = f"rename {change['path']} → {change['new_name']}"
            else:
                text = f"delete {change['path']}"
            ui.label(f"• {text}").classes("text-caption")


@ui.refreshable
def _build_output_section(checkbox: ui.checkbox) -> None:
    """Output path selector + overwrite toggle."""
    ui.label("Output path:").classes("font-bold pt-2")
    with ui.row().classes("w-full items-center"):
        output_input = ui.input(placeholder="/path/to/output.h5").classes("flex-grow")
        output_input.bind_value(app.storage.user, "output_path")
        ui.button(
            icon="folder_open",
            on_click=lambda: _pick_output_path(),
        )

    # The "Reemplazar" toggle is the same as apply_to_new_file at the top.
    ui.checkbox("Reemplazar si existe").bind_value(checkbox, "value")


@ui.refreshable
def _build_apply_buttons() -> None:
    """Restore + Apply buttons."""
    with ui.row().classes("w-full justify-end gap-2 pt-4"):
        ui.button("Restore", icon="restore", on_click=_restore_changes).props("outline")
        ui.button("Apply", icon="save", on_click=_apply_changes).props("color=primary")


# ── Event handlers ──────────────────────────────────────────────────


def _on_select(event: Any) -> None:
    if event.value:
        app.storage.user["selected_node"] = event.value
        _build_selected_info.refresh()


def _queue_rename(new_name: str) -> None:
    """Add a rename change to pending_changes."""
    new_name = (new_name or "").strip()
    if not new_name:
        ui.notify("Enter a name first", type="warning")
        return
    if "/" in new_name:
        ui.notify("Name cannot contain '/'", type="negative")
        return
    node = app.storage.user.get("selected_node")
    if not node:
        ui.notify("Select a node first", type="warning")
        return
    if node == "/":
        ui.notify("Cannot rename the root group", type="negative")
        return
    pending = list(app.storage.user.get("pending_changes", []))
    pending.append({"action": "rename", "path": node, "new_name": new_name})
    app.storage.user["pending_changes"] = pending
    _build_editor_tree_panel.refresh()
    _build_pending_list.refresh()
    ui.notify(
        f"Queued: rename {os.path.basename(node)} → {new_name}", type="positive"
    )


def _confirm_queue_delete() -> None:
    """Open confirmation dialog before queueing a delete."""
    node = app.storage.user.get("selected_node")
    if not node:
        ui.notify("Select a node first", type="warning")
        return
    if node == "/":
        ui.notify("Cannot delete the root group", type="negative")
        return

    with ui.dialog() as dialog, ui.card():
        ui.label(f"Delete '{node}'?").classes("text-h6")
        ui.label("This action will be queued and applied on Apply.").classes(
            "text-grey"
        )
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("outline")
            ui.button(
                "Delete",
                on_click=lambda: _do_queue_delete(node, dialog),
                color="negative",
            )
    dialog.open()


def _do_queue_delete(node: str, dialog: ui.dialog) -> None:
    pending = list(app.storage.user.get("pending_changes", []))
    pending.append({"action": "delete", "path": node})
    app.storage.user["pending_changes"] = pending
    dialog.close()
    _build_editor_tree_panel.refresh()
    _build_pending_list.refresh()
    ui.notify(f"Queued: delete {node}", type="positive")


def _restore_changes() -> None:
    """Empty pending_changes and refresh the tree."""
    app.storage.user["pending_changes"] = []
    _build_editor_tree_panel.refresh()
    _build_pending_list.refresh()
    ui.notify("Pending changes cleared")


def _apply_changes() -> None:
    """Apply pending changes to the output file."""
    source = app.storage.user.get("h5_path")
    if not source or not os.path.isfile(source):
        ui.notify("No source file open", type="negative")
        return
    pending = app.storage.user.get("pending_changes", [])
    if not pending:
        ui.notify("No pending changes", type="warning")
        return

    # Decide output path. If apply_to_new_file is False (default), the
    # user wants to overwrite the source itself — apply_changes already
    # supports this via overwrite=True. Otherwise, use output_path.
    apply_to_new = app.storage.user.get("apply_to_new_file", False)
    if apply_to_new:
        output = app.storage.user.get("output_path", "").strip()
        if not output:
            ui.notify("Specify an output path first", type="warning")
            return
        overwrite = app.storage.user.get("reemplazar", False)
    else:
        # Overwrite the source itself (with the user's explicit "Apply").
        output = source
        overwrite = True

    try:
        apply_changes(source, pending, output, overwrite=overwrite)
    except FileExistsError:
        ui.notify(
            "Output exists; enable 'Reemplazar' or change the path", type="negative"
        )
        return
    except (ValueError, KeyError, OSError) as e:
        ui.notify(f"Apply failed: {e}", type="negative")
        return

    app.storage.user["pending_changes"] = []
    ui.notify(f"Applied {len(pending)} changes to {output}", type="positive")
    _build_editor_tree_panel.refresh()
    _build_pending_list.refresh()


def _pick_output_path() -> None:
    """Open the file picker (hybrid native/browser) and store result."""
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
            app.storage.user["output_path"] = files[0]

    # Defer the coroutine to NiceGUI's event loop.
    ui.timer(0.0, _pick, once=True)
