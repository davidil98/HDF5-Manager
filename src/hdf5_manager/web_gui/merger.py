"""Merger tab: copy groups between HDF5 files."""

from __future__ import annotations

from nicegui import ui


def create_merger_tab() -> None:
    """Build the Merger tab layout: two file trees side by side."""
    ui.label("Merger").classes("text-h5 p-4")
    ui.label("Copy groups between two HDF5 files.").classes("text-grey text-sm px-4")
    ui.separator()
    with ui.column().classes("p-4"):
        ui.label("Select source and destination files to merge groups.")
        ui.label("(Feature coming soon)").classes("text-grey text-sm")
