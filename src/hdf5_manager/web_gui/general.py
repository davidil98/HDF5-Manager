"""Local file picker dialog adapted from NiceGUI examples.

Original: https://github.com/zauberzeug/nicegui/blob/main/examples/local_file_picker/main.py

Adapted and improved for HDF5 Manager.

Usage as a standalone dialog:
    result = await LocalFilePicker(directory="~", multiple=False)
    # result is a list[str] of selected paths, or None if cancelled.
"""

import platform
from pathlib import Path

from nicegui import events, ui


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
    ) -> None:
        """Initialize the file picker.

        Args:
            directory: Starting directory path.
            upper_limit: Directory to stop navigation at
                (None = no limit, ... = same as starting directory).
            multiple: Allow multi-select.
            show_hidden_files: Include dotfiles.
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

        with self, ui.card():
            self.add_drives_toggle()
            self.grid = ui.aggrid(
                {
                    "columnDefs": [{"field": "name", "headerName": "File"}],
                    "rowSelection": "single" if not multiple else "multiple",
                },
                html_columns=[0],
            ).classes("w-96").on("cellDoubleClicked", self.handle_double_click)
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=self.close).props("outline")
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
