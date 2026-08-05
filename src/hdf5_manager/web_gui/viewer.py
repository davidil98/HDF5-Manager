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

from hdf5_manager.core.tree import build_tree


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

    # TODO: replace this with real data once you finish the review.
    # Hint: use h5py.File(path, 'r') as a context manager, call
    # build_tree(f), and pass the result to ui.tree(). The "with"
    # block guarantees the file handle is closed even if building
    # the tree raises.
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


def _build_attributes_panel() -> None:
    """Upper right panel: node attributes.

    Placeholder. Will be populated from h5py when a tree node is
    selected (e.g. for ``/group/curve_000`` show its ``V_DS`` and
    ``timestamp`` attributes).
    """
    ui.label("Attributes").classes("text-subtitle2 p-2 pb-0")
    ui.label("Select a node to view attributes").classes(
        "text-grey text-sm p-2"
    )


def _build_dataset_preview() -> None:
    """Lower right panel: dataset contents preview.

    Placeholder. Will render an ``ui.aggrid`` from a pandas DataFrame
    once a dataset node is selected.
    """
    ui.label("Dataset Preview").classes("text-subtitle2 p-2 pb-0")
    ui.label("Select a dataset to preview its contents").classes(
        "text-grey text-sm p-2"
    )


def _on_tree_select(event) -> None:
    """Handle tree node selection.

    Args:
        event: NiceGUI TreeEventArguments. ``event.value`` is the id
            of the selected node, e.g. ``"/batch2_muestra1_01/curve_000"``
            or ``"/batch2_muestra1_01/curve_000/measured_I_DS"``.

    TODO: implement the actual logic:
        - if the node is a group: show its attributes in the right panel
        - if the node is a dataset: show its attributes AND render
          the data as a DataFrame in an ``ui.aggrid`` (paginated for
          large arrays)
        - use ``app.storage.user["h5_path"]`` to reopen the file, or
          (better) cache the open ``h5py.File`` handle somewhere
          shared so you don't reopen on every click.

    For now this just notifies the selection so you can verify the
    wiring is working end-to-end.
    """
    if event.value:
        node_id = event.value
        ui.notify(f"Selected: {node_id}")
