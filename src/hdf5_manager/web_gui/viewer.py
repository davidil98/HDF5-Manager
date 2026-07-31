"""Viewer tab: browse HDF5 tree, view attributes, preview dataset contents."""

from __future__ import annotations

from nicegui import ui


def create_viewer_tab() -> None:
    """Build the Viewer tab layout: tree + attributes + dataset preview."""
    path = ui.label("No file loaded").classes("text-grey text-sm p-2")

    with ui.splitter(limits=(250, 500)).classes("w-full flex-grow") as splitter:
        with splitter.before:
            _build_tree_panel(path)
        with splitter.after:
            with ui.column().classes("w-full h-full"):
                _build_attributes_panel()
                _build_dataset_preview()


def _build_tree_panel(path_label: ui.label) -> ui.tree:
    """Left panel: HDF5 file tree."""
    ui.label("Structure").classes("text-subtitle2 p-2 pb-0")

    tree_data: list[dict] = []
    tree = ui.tree(
        tree_data,
        label_key="label",
        node_key="id",
        on_select=lambda e: _on_tree_select(e, path_label),
    ).classes("w-full h-full overflow-auto")

    return tree


def _build_attributes_panel() -> None:
    """Upper right panel: node attributes."""
    ui.label("Attributes").classes("text-subtitle2 p-2 pb-0")
    ui.label("Select a node to view attributes").classes("text-grey text-sm p-2")


def _build_dataset_preview() -> None:
    """Lower right panel: dataset contents preview."""
    ui.label("Dataset Preview").classes("text-subtitle2 p-2 pb-0")
    ui.label("Select a dataset to preview its contents").classes(
        "text-grey text-sm p-2"
    )


def _on_tree_select(event, path_label: ui.label) -> None:
    """Handle tree node selection."""
    if event.value:
        node_id = event.value
        path_label.set_text(node_id)
