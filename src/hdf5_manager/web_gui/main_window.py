"""Main window with tabbed interface: Viewer | Editor | Merger | Export."""

from nicegui import app, ui

# Single page build
@ui.page("/")
def index() -> None:
    """Build the main application layout."""
    with ui.column().classes("w-full h-screen"):
        _build_toolbar()        # Open File Button + path label
        _build_tabs()          # Viewer | Editor | Merger | Export

def _build_toolbar():
    """File path display and open button."""
    with ui.row().classes("w-full items-center gap-2 p-2"):
        async def _pick_file():
            files = await app.native.main_window.create_file_dialog(
                allow_multiple=False, file_types=("HDF5 files (*.h5;*.hdf5)",)
            )
            #app.storage.user['h5_path'] = "Aquí va el label del file"

        ui.button("Open File", icon="folder_open", on_click=_pick_file)
        app.storage.user['h5_path'] = "None"
        file_path_label = ui.label().bind_text_from(app.storage.user, 'h5_path') # label en None


def _build_tabs() -> None:
    """Build the tabbed interface."""


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
        reload=True,
        storage_secret="hdf5-manager-secret",
    )

if __name__ in {"__main__", "__mp_main__"}:
    run()
