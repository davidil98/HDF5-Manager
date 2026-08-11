"""Exporter tab: export HDF5 datasets to CSV or Excel."""

from __future__ import annotations

from nicegui import ui, app
import os
import h5py
from hdf5_manager.core.tree import build_tree

@ui.refreshable
def create_exporter_tab() -> None:
    """Build the Exporter tab layout."""
    path = app.storage.user.get("h5_path", "No file selected")

    with ui.row().classes("w-full items-center gap-2 p-2"):
        ui.label("File:").classes("font-bold")
        if path != "No file selected":
            ui.label(os.path.basename(path)).classes("text-grey text-sm truncate")
        else:
            ui.label(path).classes("text-grey text-sm truncate")

    with ui.splitter(limits=(250, 500)).classes("w-full flex-grow") as splitter:
        with splitter.before:
            _build_tree_checkboxes_panel(path)
        with splitter.after:
            with ui.column().classes("w-full h-full"):
                _build_selected_groups_panel()
                _build_config_export_panel()

@ui.refreshable
def _build_tree_checkboxes_panel(path: str) -> ui.tree:
    """Left panel: HDF5 file tree with checkboxes.

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
        tick_strategy='leaf'     
    ).classes("w-full h-full overflow-auto")

    return tree

@ui.refreshable
def _build_selected_groups_panel() -> None:
    """Show list of selected groups."""
    ui.button("Select All Groups")
    ui.label("Selected Groups").classes("font-bold")
    ui.label("No groups selected").classes("text-grey text-sm")

@ui.refreshable
def _build_config_export_panel() -> None:
    """Show configuration for exporting."""
    ui.label("Export Configuration").classes("font-bold")
    ui.label("No groups selected").classes("text-grey text-sm")