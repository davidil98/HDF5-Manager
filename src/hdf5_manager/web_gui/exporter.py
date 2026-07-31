"""Exporter tab: export HDF5 datasets to CSV or Excel."""

from __future__ import annotations

from nicegui import ui


def create_exporter_tab() -> None:
    """Build the Exporter tab layout."""
    ui.label("Export").classes("text-h5 p-4")
    ui.label("Export HDF5 data to CSV or Excel files.").classes(
        "text-grey text-sm px-4"
    )
    ui.separator()
    with ui.column().classes("p-4"):
        ui.label("Select groups and datasets to export.")
        ui.label("(Feature coming soon)").classes("text-grey text-sm")
