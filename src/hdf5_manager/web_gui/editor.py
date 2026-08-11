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

from hdf5_manager.core.operations import apply_changes, default_output_path
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
            old_path = node["id"]
            parent = "/".join(old_path.split("/")[:-1])
            new_path = f"{parent}/{new_name}" if parent else f"/{new_name}"
            node["id"] = new_path
            node["label"] = new_name
            _virtual_rebase_children(node["children"], old_path, new_path)
            return True
        if node.get("children"):
            if _virtual_rename(node["children"], path, new_name):
                # Update descendants' ids since their parent path changed.
                parent = "/".join(path.split("/")[:-1])
                new_path = f"{parent}/{new_name}" if parent else f"/{new_name}"
                _virtual_rebase_children(node["children"], path, new_path)
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
                _build_output_section()
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
def _build_output_section() -> None:
    """Source file (read-only) and output path selector.

    ``output_path`` is initialized to ``<source>-edit.<ext>`` whenever a
    new source is loaded (see ``main_window._pick_file``); this section
    just renders and lets the user edit or re-pick it.
    """
    source = app.storage.user.get("h5_path") or ""
    ui.label("Source file:").classes("font-bold pt-2")
    ui.label(source or "(no file loaded)").classes("text-grey text-sm").style(
        "word-break: break-all; white-space: normal;"
    )

    ui.label("Output path:").classes("font-bold pt-2")
    with ui.row().classes("w-full items-center"):
        output_input = ui.input(placeholder="/path/to/output.h5").classes("flex-grow")
        output_input.bind_value(app.storage.user, "output_path")
        ui.button(
            icon="folder_open",
            on_click=lambda: _pick_output_path(),
        )


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
    """Add a rename change to pending_changes.

    If the requested name collides with an existing sibling in the
    virtual tree, ``_edit`` is appended until a free name is found.
    """
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

    current_label = os.path.basename(node)
    siblings = _virtual_sibling_labels(node)
    final_name = _unique_sibling_name(siblings, current_label, new_name)
    if final_name != new_name:
        ui.notify(
            f"'{new_name}' already exists; using '{final_name}'", type="info"
        )

    parent = "/".join(node.split("/")[:-1])
    new_path = f"{parent}/{final_name}" if parent else f"/{final_name}"

    pending = list(app.storage.user.get("pending_changes", []))
    pending.append({"action": "rename", "path": node, "new_name": final_name})
    app.storage.user["pending_changes"] = pending
    # Keep selected_node in sync with the updated virtual tree so that
    # follow-up operations (rename, delete) on the same node reference
    # the new id, not the stale one.
    app.storage.user["selected_node"] = new_path
    _build_editor_tree_panel.refresh()
    _build_pending_list.refresh()
    _build_selected_info.refresh()
    ui.notify(
        f"Queued: rename {current_label} → {final_name}", type="positive"
    )


# ── Sibling-name collision helpers ─────────────────────────────────


def _find_node(nodes: list[dict], path: str) -> dict | None:
    """Return the node with id == path, or None if not found."""
    for n in nodes:
        if n["id"] == path:
            return n
        if n.get("children"):
            found = _find_node(n["children"], path)
            if found is not None:
                return found
    return None


def _virtual_sibling_labels(selected_path: str) -> set[str]:
    """Return the set of basenames among siblings of *selected_path*.

    The siblings are taken from the current virtual tree (source plus
    pending changes), so a rename previously queued by the user is
    correctly considered as occupied.
    """
    parent_path = "/".join(selected_path.split("/")[:-1])
    source = app.storage.user.get("h5_path")
    pending = app.storage.user.get("pending_changes", [])
    if not source or not os.path.isfile(source):
        return set()
    with h5py.File(source, "r") as f:
        raw_tree = build_tree(f)
    virtual_tree = apply_virtual_changes(raw_tree, pending)
    if not parent_path or parent_path == "/":
        return {n["label"] for n in virtual_tree}
    parent = _find_node(virtual_tree, parent_path)
    if parent is None:
        return set()
    return {c["label"] for c in parent.get("children", [])}


def _unique_sibling_name(
    siblings: set[str], current_label: str, requested: str
) -> str:
    """Return a sibling name that does not collide.

    If *requested* is already used by a *different* sibling, ``_edit``
    is appended repeatedly until a free name is found. The current
    label of the node is excluded from the collision check so a
    no-op rename (renaming to the same name) is accepted as-is.
    """
    candidate = requested
    while candidate in siblings and candidate != current_label:
        candidate = f"{candidate}_edit"
    return candidate


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
    """Apply pending changes to the output path.

    The destination is taken from ``app.storage.user["output_path"]``; if it
    is empty, it falls back to ``<source>-edit.<ext>``. When the destination
    is the source itself or already exists on disk, an explicit confirmation
    dialog is shown before mutating anything.
    """
    source = app.storage.user.get("h5_path")
    if not source or not os.path.isfile(source):
        ui.notify("No source file open", type="negative")
        return
    pending = app.storage.user.get("pending_changes", [])
    if not pending:
        ui.notify("No pending changes", type="warning")
        return

    output = (app.storage.user.get("output_path") or "").strip()
    if not output:
        output = default_output_path(source)
        app.storage.user["output_path"] = output

    overwrite_target = (
        os.path.abspath(output) == os.path.abspath(source)
        or os.path.exists(output)
    )
    if overwrite_target:
        _confirm_apply(source, output, pending)
    else:
        _do_apply(source, output, pending)


def _confirm_apply(source: str, output: str, pending: list[dict[str, Any]]) -> None:
    """Ask the user before overwriting the source or an existing destination."""
    same_as_source = os.path.abspath(output) == os.path.abspath(source)
    label = "the source file" if same_as_source else f"'{os.path.basename(output)}'"

    def _on_overwrite() -> None:
        dialog.close()
        _do_apply(source, output, pending)

    with ui.dialog() as dialog, ui.card():
        ui.label(f"{label} will be overwritten").classes("text-h6")
        ui.label(
            f"{len(pending)} pending change(s) will be applied. "
            "This cannot be undone."
        ).classes("text-grey")
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("outline")
            ui.button("Overwrite", on_click=_on_overwrite, color="negative")
    dialog.open()


def _do_apply(source: str, output: str, pending: list[dict[str, Any]]) -> None:
    """Run ``apply_changes`` and refresh the editor UI on success."""
    try:
        apply_changes(source, pending, output, overwrite=True)
    except (FileExistsError, ValueError, KeyError, OSError) as e:
        ui.notify(f"Apply failed: {e}", type="negative")
        return

    app.storage.user["pending_changes"] = []
    app.storage.user["selected_node"] = None
    ui.notify(f"Applied {len(pending)} changes to {output}", type="positive")
    _build_editor_tree_panel.refresh()
    _build_pending_list.refresh()
    _build_selected_info.refresh()


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
