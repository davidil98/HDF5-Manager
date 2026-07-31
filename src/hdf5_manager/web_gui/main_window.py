"""Main window with tabbed interface: Viewer | Editor | Merger | Export."""

from __future__ import annotations

from nicegui import app, ui

from hdf5_manager.web_gui.editor import create_editor_tab
from hdf5_manager.web_gui.exporter import create_exporter_tab
from hdf5_manager.web_gui.merger import create_merger_tab
from hdf5_manager.web_gui.viewer import create_viewer_tab


@ui.page("/")
def index() -> None:
    """Build the main application layout."""
    with ui.column().classes("w-full h-screen"):
        _build_toolbar()
        _build_tabs()


def _build_toolbar() -> None:
    """File path display and open button."""
    with ui.row().classes("w-full items-center gap-2 p-2"):
        ui.button("Open File...", icon="folder_open", on_click=_open_file_dialog)
        app.storage.user["h5_path"] = ""
        ui.label().bind_text_from(app.storage.user, "h5_path").classes(
            "text-grey text-sm truncate"
        )


async def _open_file_dialog() -> None:
    """Open a native-looking file dialog and load the HDF5 file."""
    files = await app.native.main_window.create_file_dialog(
        allow_multiple=False, file_types=("HDF5 files (*.h5 *.hdf5)",)
    )
    if files:
        path = files[0]
        app.storage.user["h5_path"] = path


def _build_tabs() -> None:
    """Build the tabbed interface."""
    with ui.tabs().classes("w-full") as tabs:
        ui.tab("viewer", label="Viewer", icon="visibility")
        ui.tab("editor", label="Editor", icon="edit")
        ui.tab("merger", label="Merger", icon="merge")
        ui.tab("export", label="Export", icon="file_download")

    with ui.tab_panels(tabs, value="viewer").classes("w-full flex-grow"):
        with ui.tab_panel("viewer"):
            create_viewer_tab()
        with ui.tab_panel("editor"):
            create_editor_tab()
        with ui.tab_panel("merger"):
            create_merger_tab()
        with ui.tab_panel("export"):
            create_exporter_tab()


def run() -> None:
    """Launch the standalone NiceGUI application."""
    import sys

    # Native mode needs freeze_support on Windows when packaged
    if sys.platform == "win32":
        from multiprocessing import freeze_support

        freeze_support()

    ui.run(
        title="HDF5 Manager",
        favicon="📊",
        native=True,
        window_size=(1200, 800),
        reload=False,
        storage_secret="hdf5-manager-secret",
    )
