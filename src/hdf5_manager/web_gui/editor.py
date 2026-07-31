"""Editor tab: rename and delete HDF5 groups and datasets."""

from __future__ import annotations

from nicegui import ui


def create_editor_tab() -> None:
    """Build the Editor tab layout."""
    ui.label("Editor").classes("text-h5 p-4")
    ui.label("Rename and delete groups and datasets.").classes("text-grey text-sm px-4")
    ui.separator()
    with ui.column().classes("p-4"):
        ui.label("Select a file in the Viewer tab, then switch here to edit.")
        ui.label("(Feature coming soon)").classes("text-grey text-sm")
