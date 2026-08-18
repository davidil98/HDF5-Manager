"""Local file picker dialog adapted from NiceGUI examples.

Original: https://github.com/zauberzeug/nicegui/blob/main/examples/local_file_picker/main.py

Adapted and improved for HDF5 Manager.

Usage as a standalone dialog:
    result = await LocalFilePicker(directory="~", multiple=False)
    # result is a list[str] of selected paths, or None if cancelled.
"""

import platform
from pathlib import Path
from typing import Any

from nicegui import app, events, ui


def picker_start_directory(path: str | None) -> str:
    """Return an existing directory suitable for starting a file dialog."""
    candidate = Path(path).expanduser() if path else Path.home()
    if candidate.is_dir():
        return str(candidate)
    for parent in candidate.parents:
        if parent.is_dir():
            return str(parent)
    return str(Path.home())


def _native_dialog_type(name: str, legacy_name: str) -> Any:
    """Resolve a pywebview dialog enum across supported versions."""
    import webview

    file_dialog = getattr(webview, "FileDialog", None)
    if file_dialog is not None and hasattr(file_dialog, name):
        return getattr(file_dialog, name)
    return getattr(webview, legacy_name)


def _normalise_paths(paths: Any) -> list[str]:
    """Normalize native tuples and web picker lists to a list of strings."""
    return [str(path) for path in (paths or [])]


async def pick_file(
    *,
    directory: str = "~",
    multiple: bool = False,
    file_types: tuple[str, ...] = (),
    extensions: tuple[str, ...] = (),
) -> list[str]:
    """Open a native or web file picker and return selected paths."""
    if app.native.main_window:
        files = await app.native.main_window.create_file_dialog(
            dialog_type=_native_dialog_type("OPEN", "OPEN_DIALOG"),
            directory=picker_start_directory(directory),
            allow_multiple=multiple,
            file_types=file_types,
        )
    else:
        files = await LocalFilePicker(
            directory=picker_start_directory(directory),
            multiple=multiple,
            file_extensions=extensions,
        )
    return _normalise_paths(files)


async def pick_save_file(
    *,
    path: str = "",
    save_filename: str = "",
    file_types: tuple[str, ...] = (),
    extensions: tuple[str, ...] = (),
) -> list[str]:
    """Open a save dialog, retaining a web fallback with an editable path."""
    directory = picker_start_directory(path)
    if app.native.main_window:
        files = await app.native.main_window.create_file_dialog(
            dialog_type=_native_dialog_type("SAVE", "SAVE_DIALOG"),
            directory=directory,
            allow_multiple=False,
            save_filename=save_filename,
            file_types=file_types,
        )
    else:
        files = await LocalFilePicker(
            directory=directory,
            multiple=False,
            file_extensions=extensions,
        )
    return _normalise_paths(files)


async def pick_directory(*, directory: str = "~") -> list[str]:
    """Open a native or web directory picker and return selected paths."""
    if app.native.main_window:
        files = await app.native.main_window.create_file_dialog(
            dialog_type=_native_dialog_type("FOLDER", "FOLDER_DIALOG"),
            directory=picker_start_directory(directory),
            allow_multiple=False,
        )
    else:
        files = await LocalFilePicker(
            directory=picker_start_directory(directory),
            select_directory=True,
        )
    return _normalise_paths(files)


class LocalFilePicker(ui.dialog):
    """Web-based file browser dialog (no pywebview required).

    Works in both browser mode and native mode. In native mode, prefer
    ``app.native.main_window.create_file_dialog`` for the OS-native file dialog.
    """

    def __init__(
        self,
        directory: str,
        *,
        upper_limit: str | None = ...,
        multiple: bool = False,
        show_hidden_files: bool = False,
        select_directory: bool = False,
        file_extensions: tuple[str, ...] = (),
    ) -> None:
        """Initialize the file picker.

        Args:
            directory: Starting directory path.
            upper_limit: Directory to stop navigation at
                (None = no limit, ... = same as starting directory).
            multiple: Allow multi-select.
            show_hidden_files: Include dotfiles.
            select_directory: Return the currently browsed directory instead
                of selecting a file.
        """
        super().__init__()

        self.path = Path(directory).expanduser()
        if upper_limit is None:
            self.upper_limit = None
        else:
            self.upper_limit = Path(
                directory if upper_limit is ... else upper_limit
            ).expanduser()
        self.show_hidden_files = show_hidden_files
        self.select_directory = select_directory
        self.file_extensions = tuple(
            extension.lower()
            if extension.startswith(".")
            else f".{extension.lower()}"
            for extension in file_extensions
        )

        with self, ui.card():
            self.add_drives_toggle()
            self.grid = (
                ui.aggrid(
                    {
                        "columnDefs": [{"field": "name", "headerName": "File"}],
                        "rowSelection": "single" if not multiple else "multiple",
                    },
                    html_columns=[0],
                )
                .classes("w-96")
                .on("cellDoubleClicked", self.handle_double_click)
            )
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=self.close).props("outline")
                if self.select_directory:
                    ui.button("Select this folder", on_click=self._select_directory)
                else:
                    ui.button("Ok", on_click=self._handle_ok)
        self.update_grid()

    def add_drives_toggle(self) -> None:
        """Add drive selector on Windows (e.g. C:, D:)."""
        if platform.system() == "Windows":
            try:
                import win32api

                drives = win32api.GetLogicalDriveStrings().split("\000")[:-1]
                self.drives_toggle = ui.toggle(
                    drives, value=drives[0], on_change=self.update_drive
                )
            except ImportError:
                # win32api no instalado — se omite el selector de unidades.
                pass

    def update_drive(self) -> None:
        """Switch to the selected drive."""
        self.path = Path(self.drives_toggle.value).expanduser()
        self.update_grid()

    def update_grid(self) -> None:
        """Refresh the file listing for the current directory."""
        paths = list(self.path.glob("*"))
        if not self.show_hidden_files:
            paths = [p for p in paths if not p.name.startswith(".")]
        if self.file_extensions:
            paths = [
                p
                for p in paths
                if p.is_dir() or p.suffix.lower() in self.file_extensions
            ]
        # Sort: directories first, then alphabetical.
        paths.sort(key=lambda p: p.name.lower())
        paths.sort(key=lambda p: not p.is_dir())

        self.grid.options["rowData"] = [
            {
                "name": f"📁 <strong>{p.name}</strong>" if p.is_dir() else p.name,
                "path": str(p),
            }
            for p in paths
        ]
        # ".." parent directory navigation.
        if (self.upper_limit is None and self.path != self.path.parent) or (
            self.upper_limit is not None and self.path != self.upper_limit
        ):
            self.grid.options["rowData"].insert(
                0,
                {
                    "name": "📁 <strong>..</strong>",
                    "path": str(self.path.parent),
                },
            )
        self.grid.update()

    def handle_double_click(self, e: events.GenericEventArguments) -> None:
        """Navigate into directory or submit the selected file."""
        self.path = Path(e.args["data"]["path"])
        if self.path.is_dir():
            self.update_grid()
        else:
            # Submit returns the selected path wrapped in a list.
            self.submit([str(self.path)])

    async def _handle_ok(self) -> None:
        """Submit selected rows from the AG Grid."""
        rows = await self.grid.get_selected_rows()
        self.submit([r["path"] for r in rows])

    def _select_directory(self) -> None:
        """Submit the directory currently shown by the picker."""
        self.submit([str(self.path)])
