"""About dialog: version, authorship, licence and institutional contact."""

from __future__ import annotations

from nicegui import ui

from hdf5_manager import app_info


def open_about_dialog() -> None:
    """Show the application information dialog.

    The dialog is rebuilt on every click, so ``app_info.app_version()`` is
    evaluated at open time instead of being frozen at import time.
    """
    with ui.dialog() as dialog, ui.card().classes("w-96 gap-2"):
        ui.label(app_info.APP_NAME).classes("text-lg font-bold")
        ui.label(f"Version {app_info.app_version()}").classes("text-sm text-grey")
        ui.separator()
        ui.label(app_info.DESCRIPTION).classes("text-sm")
        ui.label(app_info.INSTITUTION).classes("text-sm")
        ui.label(app_info.AUTHOR).classes("text-sm")
        if app_info.CONTACT_EMAIL:
            ui.link(
                app_info.CONTACT_EMAIL,
                f"mailto:{app_info.CONTACT_EMAIL}",
            ).classes("text-sm")
        ui.label(f"License: {app_info.LICENSE_NAME}").classes("text-sm")
        ui.link(
            "Source code and releases",
            app_info.REPOSITORY_URL,
            new_tab=True,
        ).classes("text-sm")
        with ui.row().classes("w-full justify-end"):
            ui.button("Close", on_click=dialog.close).props("flat")

    dialog.open()
