"""Main window with tabbed interface: Viewer | Editor | Merger | Export."""

from nicegui import app, ui

from hdf5_manager.web_gui.editor import create_editor_tab
from hdf5_manager.web_gui.exporter import create_exporter_tab
from hdf5_manager.web_gui.general import LocalFilePicker
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
        """File picker híbrido — native o browser según el runtime.

        En modo nativo (``ui.run(native=True)``) usa
        ``app.native.main_window.create_file_dialog``, que invoca el
        file dialog del sistema operativo a través de pywebview.

        En modo navegador usa ``local_file_picker``, un diálogo web
        que emula un explorador de archivos dentro de la UI sin
        necesidad de pywebview.
        """
        if app.native.main_window:
            # Modo nativo: diálogo del SO, filtra extensiones .h5
            files = await app.native.main_window.create_file_dialog(
                allow_multiple=False,
                file_types=("HDF5 files (*.h5;*.hdf5)", "All files (*.*)"),
            )
        else:
            # Modo navegador: explorador web genérico (sin filtro de extensiones).
            # '~' es el home del usuario como directorio inicial.
            # La llamada devuelve una lista (ej: ['/home/user/datos.h5']) o None.
            files = await LocalFilePicker(directory="~", multiple=False)
            ui.notify(f'You selected {files[0]}')

        if files:
            app.storage.user["h5_path"] = files[0]

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


def run() -> None:
    """Launch the standalone NiceGUI application."""
    import sys

    # Native mode needs freeze_support on Windows when packaged.
    # Debe ser la PRIMERA llamada en el proceso principal.
    if sys.platform == "win32":
        from multiprocessing import freeze_support

        freeze_support()

    ui.run(
        title="HDF5 Manager",
        favicon="📊",
        native=False,
        #window_size=(1200, 800),
        reload=True,
        storage_secret="hdf5-manager-secret",
    )


if __name__ in {"__main__", "__mp_main__"}:
    run()
