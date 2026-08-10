"""Viewer tab: browse HDF5 tree, view attributes, preview dataset contents.

The whole tab is wrapped in ``@ui.refreshable`` so the toolbar's
``_pick_file`` callback can call ``create_viewer_tab.refresh()`` after
the user selects a new file, forcing a full rebuild of the tree and
preview panels.

Reactive data flow:

    User clicks "Open File" in the toolbar
        -> app.storage.user["h5_path"] = selected_path
        -> create_viewer_tab.refresh()
            -> reads new path from app.storage
            -> opens h5py.File, builds tree_data
            -> re-renders the ui.tree, attributes, preview
"""

from __future__ import annotations

import os

import h5py
from nicegui import app, ui

from hdf5_manager.core.tree import _attr_to_python, build_tree, get_node


@ui.refreshable
def create_viewer_tab() -> None:
    """Build the Viewer tab layout: tree + attributes + dataset preview.

    Reads the current HDF5 file path from ``app.storage.user["h5_path"]``,
    which is set by the toolbar's file picker. When the path is
    invalid or absent, the tree is empty and the panels show placeholders.
    """
    # NOTE: always read from app.storage at this point. Reading once at
    # module import time would freeze the value to the initial state.
    path = app.storage.user.get("h5_path", "No file selected")

    with ui.row().classes("w-full items-center gap-2 p-2"):
        ui.label("File:").classes("font-bold")
        if path != "No file selected":
            # Show just the basename so the toolbar stays compact.
            ui.label(os.path.basename(path)).classes("text-grey text-sm truncate")
        else:
            ui.label(path).classes("text-grey text-sm truncate")

    with ui.splitter(limits=(250, 500)).classes("w-full flex-grow") as splitter:
        with splitter.before:
            _build_tree_panel(path)
        with splitter.after:
            with ui.column().classes("w-full h-full"):
                _build_attributes_panel()
                _build_dataset_preview()


def _build_tree_panel(path: str) -> ui.tree:
    """Left panel: HDF5 file tree.

    Opens the file in read-only mode and populates the tree with the
    full hierarchy via ``build_tree()``. If the path is not a valid
    file (e.g. user hasn't picked one yet), the tree is empty.

    Args:
        path: Absolute path to the HDF5 file, or the placeholder string
            "No file selected" when nothing has been chosen.
    """
    ui.label("Structure").classes("text-subtitle2 p-2 pb-0")

    # Build tree
    tree_data: list[dict] = []
    if os.path.isfile(path):
        with h5py.File(path, "r") as f:
            tree_data = build_tree(f)

    tree = ui.tree(
        tree_data,
        label_key="label",
        node_key="id",
        # TODO: replace with a real handler. e.value will be the
        # selected node id (e.g. "/group/curve_000/measured_I_DS").
        # You'll want to look up the node's attributes and data
        # in the right-panel widgets.
        on_select=lambda e: _on_tree_select(e),
    ).classes("w-full h-full overflow-auto")

    return tree


@ui.refreshable
def _build_attributes_panel() -> None:
    """Upper right panel: node attributes.

    Placeholder. Will be populated from h5py when a tree node is
    selected (e.g. for ``/group/curve_000`` show its ``V_DS`` and
    ``timestamp`` attributes).
    """
    ui.label("Attributes").classes("text-subtitle2 p-2 pb-0")
    node_id = app.storage.user.get("selected_node", None)
    if not node_id:
        ui.label("Select a node to view attributes").classes("text-grey text-sm p-2")
        return
    path = app.storage.user.get("h5_path", None)
    if not path or not os.path.isfile(path):
        ui.label("No file open").classes("text-grey text-sm p-2")
        return
    with h5py.File(path, "r") as f:
        node = get_node(f, node_id)
        attrs = {k: _attr_to_python(v) for k, v in node.attrs.items()}
    if not attrs:
        ui.label("No attributes").classes("text-grey text-sm p-2")
        return
    ui.table(
        columns=[
            {"id": "Name", "label": "Name", "field": "Name", "align": "left"},
            {"id": "Value", "label": "Value", "field": "Value", "align": "center"},
        ],
        rows=[{"Name": k, "Value": v} for k, v in attrs.items()],
        pagination=4,
    ).classes("w-full overflow-auto")


@ui.refreshable
def _build_dataset_preview() -> None:
    """Lower right panel: dataset contents preview.

    Displays the first 20 elements of a dataset (head only). Shows
    shape, dtype, and total size as a header, then a ``ui.table`` with
    the data. Supports 1D (single column) and 2D (column-per-axis) shapes;
    higher dimensions show a placeholder.
    """
    ui.label("Dataset Preview").classes("text-subtitle2 p-2 pb-0")

    node_id = app.storage.user.get("selected_node", None)
    if not node_id:
        ui.label("Select a node to view dataset contents").classes(
            "text-grey text-sm p-2"
        )
        return
    path = app.storage.user.get("h5_path", None)
    if not path or not os.path.isfile(path):
        ui.label("No file open").classes("text-grey text-sm p-2")
        return

    with h5py.File(path, "r") as f:
        node = get_node(f, node_id)
        if not isinstance(node, h5py.Dataset):
            ui.label("(not a dataset — select a dataset leaf)").classes(
                "text-grey text-sm p-2"
            )
            return

        # Header with metadata.
        ui.label(
            f"Shape: {node.shape}    Dtype: {node.dtype}    Size: {node.size:,}"
        ).classes("text-caption text-grey p-2")

        # Total number of rows along axis 0 (works for 1D and 2D).
        n = node.shape[0] if node.ndim >= 1 else 0
        head_n = min(20, n)
        if head_n == 0:
            ui.label("(empty dataset)").classes("text-grey text-sm p-2")
            return
        # Read only what we need — never the whole dataset.
        data = node[:head_n]

        if data.ndim == 1:
            columns = [
                {"name": "idx", "label": "idx", "field": "idx", "align": "right"},
                {"name": "v", "label": "value", "field": "v", "align": "left"},
            ]
            rows = [{"idx": i, "v": _attr_to_python(v)} for i, v in enumerate(data)]
        elif data.ndim == 2:
            n_cols = data.shape[1]
            columns = [
                {"name": "idx", "label": "idx", "field": "idx", "align": "right"}
            ]
            for j in range(n_cols):
                columns.append(
                    {
                        "name": f"c{j}",
                        "label": f"col_{j}",
                        "field": f"c{j}",
                        "align": "left",
                    }
                )
            rows = []
            for i in range(data.shape[0]):
                row: dict[str, object] = {"idx": i}
                for j in range(n_cols):
                    row[f"c{j}"] = _attr_to_python(data[i, j])
                rows.append(row)
        else:
            ui.label(f"(N-D preview not supported for {data.ndim}D datasets)").classes(
                "text-grey text-sm p-2"
            )
            return

    if n > head_n:
        ui.label(f"(showing first {head_n} of {n:,} rows)").classes(
            "text-caption text-grey p-1"
        )

    with ui.splitter() as splitter:
        with splitter.before:
            ui.table(columns=columns, rows=rows[0:int(len(rows)/2)], row_key="idx").classes("w-full overflow-auto")
        with splitter.after:
            ui.table(columns=columns, rows=rows[int(len(rows)/2):], row_key="idx").classes("w-full overflow-auto")


def _on_tree_select(event) -> None:
    """Handle tree node selection.

    Args:
        event: NiceGUI TreeEventArguments. ``event.value`` is the id
            of the selected node, e.g. ``"/batch2_muestra1_01/curve_000"``
            or ``"/batch2_muestra1_01/curve_000/measured_I_DS"``.
    """
    if event.value:
        app.storage.user["selected_node"] = event.value
        _build_attributes_panel.refresh()
        _build_dataset_preview.refresh()
        node_id = event.value # this can be use to notify or show selected node/item. For now, theres no plans.
