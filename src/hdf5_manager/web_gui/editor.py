"""Editor tab: rename and delete HDF5 groups and datasets."""

from __future__ import annotations

from nicegui import ui, app


def create_editor_tab() -> None:
    """Build the Editor tab layout."""
    replace_main_file = ui.checkbox("Apply changes in a new file")

    if replace_main_file:
        with ui.row().classes("w-full items-center gap-2 p-2"):
            ui.button("Select Path", icon="folder_open").bind_visibility_from(replace_main_file, 'value')
            ui.label("Output name:").bind_visibility_from(replace_main_file, 'value')
            ui.input("").bind_visibility_from(replace_main_file, 'value') # Aquí va el file path por defecto o se va construyendo con binding según se configura el path + output file name
            ui.label(".hdf5").bind_visibility_from(replace_main_file, 'value')

        with ui.row().classes("w-full items-center gap-2 p-2"):
            ui.label(f"Output Path: ").classes("font-bold") 
            ui.label("").classes("text-grey text-sm truncate") # Aquí va el path completo con el nombre del file
    
    with ui.splitter(limits=(250, 500)).classes("w-full flex-grow") as splitter:
        with splitter.before:
            _build_editor_tree_panel()
        with splitter.after:
            with ui.column().classes("w-full h-full"):
                with ui.dropdown_button("Select tool", auto_close=True):
                    ui.item("On Select") # Original: "Rename selected" y "Delete selected"
                    ui.item("Multiple Select") # Enable multiple selection tree with checkbooxes (I think it's tick_strategy)
                ui.label("Confirm changes").classes("text-subtitle2 p-2 pb-0")
                ui.button("Restore changes", icon="restore") # el actual tree es un preview de los cambios. Revierte los cambios al file original.
                ui.button("Apply changes", icon="save") # Aplica los cambios según la configuración
                

def _build_editor_tree_panel() -> ui.tree:
    """Left panel: HDF5 file tree.

    Opens the file in r+ mode and populates the tree with the
    full hierarchy via ``build_tree()``. If the path is not a valid
    file (e.g. user hasn't picked one yet), the tree is empty.

    Args:
        path: Absolute path to the HDF5 file, or the placeholder string
            "No file selected" when nothing has been chosen.
    """
    ui.label("Structure").classes("text-subtitle2 p-2 pb-0")
