"""Main window with tabbed interface: Viewer | Editor | Merger | Export."""

from pathlib import Path

from nicegui import app, ui

from hdf5_manager.core.operations import default_output_path
from hdf5_manager.web_gui.editor import create_editor_tab
from hdf5_manager.web_gui.exporter import create_exporter_tab
from hdf5_manager.web_gui.general import pick_file
from hdf5_manager.web_gui.merger import create_merger_tab
from hdf5_manager.web_gui.viewer import create_viewer_tab


@ui.page("/")
def index() -> None:
    """Build the main application layout."""
    with ui.column().classes("w-full h-screen"):
        _build_toolbar()
        _build_tabs()


def _build_toolbar() -> None:
    """File path display and open button.

    The callback pattern: ``on_click`` runs the async function but
    discards its return value, so the function must *mutate* shared
    state (``app.storage.user``) instead of returning a value.
    """
    # Initialize before binding, otherwise the label stays blank.
    app.storage.user["h5_path"] = "No file selected"

    async def _pick_file() -> None:
        """Open the shared native/web source file picker."""
        files = await pick_file(
            directory="~",
            multiple=False,
            file_types=("HDF5 files (*.h5;*.hdf5)", "All files (*.*)"),
            extensions=(".h5", ".hdf5"),
        )

        if files:
            src = files[0]
            ui.notify(f"You selected {src}")
            app.storage.user["h5_path"] = src
            app.storage.user["output_path"] = default_output_path(src)
            app.storage.user["pending_changes"] = []
            app.storage.user["selected_node"] = None
            app.storage.user["pending_merges"] = []
            app.storage.user["merger_selected_source"] = None
            app.storage.user["merger_selected_groups"] = []
            app.storage.user["export_selected_groups"] = []
            app.storage.user["export_available_groups"] = []
            source = Path(src)
            app.storage.user["export_output_dir"] = str(
                source.parent / f"{source.stem}-export"
            )
            app.storage.user["export_output_name"] = f"{source.stem}-export.csv"
            create_viewer_tab.refresh()
            create_editor_tab.refresh()
            create_merger_tab.refresh()
            create_exporter_tab.refresh()

    with ui.row().classes("w-full items-center gap-2 p-2"):
        ui.button("Open File", icon="folder_open", on_click=_pick_file)
        ui.label("File Path:").classes("pl-3 font-bold")
        # El binding actualiza automáticamente el texto cuando h5_path cambia.
        ui.label().bind_text_from(app.storage.user, "h5_path").classes(
            "text-grey text-sm truncate"
        )


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
