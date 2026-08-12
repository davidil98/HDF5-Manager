"""Exporter tab: export HDF5 datasets to CSV or Excel."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import h5py
from nicegui import app, ui

from hdf5_manager.core.export import ExportMode, export_csv, export_xlsx
from hdf5_manager.core.tree import build_tree
from hdf5_manager.web_gui.general import LocalFilePicker

_NO_FILE = "No file selected"

_EXPORT_MODES: dict[ExportMode, tuple[str, str]] = {
    "side_by_side": (
        "Datasets side by side",
        "One table per group with datasets as columns.",
    ),
    "sheets": (
        "One sheet per group",
        "One Excel workbook with one sheet for each group.",
    ),
    "per_group": (
        "One file per group",
        "One independent CSV or Excel file for each selected group.",
    ),
}


@ui.refreshable
def create_exporter_tab() -> None:
    """Build the Exporter tab layout."""
    _ensure_state()
    path = app.storage.user.get("h5_path", _NO_FILE)

    with ui.column().classes("w-full h-full gap-2"):
        with ui.row().classes("w-full items-center gap-2 p-2"):
            ui.label("File:").classes("font-bold")
            ui.label(os.path.basename(path) if path != _NO_FILE else path).classes(
                "text-grey text-sm truncate"
            )

        if path == _NO_FILE or not os.path.isfile(path):
            ui.label("Choose an HDF5 file to configure an export.").classes(
                "text-grey p-4"
            )
            return

        with ui.splitter(limits=(250, 500)).classes("w-full flex-grow") as splitter:
            with splitter.before:
                tree = _build_tree_checkboxes_panel(path)
            with splitter.after:
                with ui.column().classes("w-full h-full gap-4 p-3"):
                    _build_selected_groups_panel(tree)
                    _build_config_export_panel()


def _ensure_state() -> None:
    """Initialize exporter state without overwriting the current selection."""
    path = app.storage.user.get("h5_path", _NO_FILE)
    defaults: dict[str, Any] = {
        "export_selected_groups": [],
        "export_available_groups": [],
        "export_mode": "side_by_side",
        "export_format": "csv",
        "export_output_name": _default_output_name(path, "csv"),
        "export_output_dir": _default_output_dir(path),
    }
    for key, value in defaults.items():
        if key not in app.storage.user:
            app.storage.user[key] = value


def _default_output_dir(path: str) -> str:
    """Return a predictable export directory next to the source file."""
    if path == _NO_FILE:
        return ""
    source = Path(path)
    return str(source.parent / f"{source.stem}-export")


@ui.refreshable
def _build_tree_checkboxes_panel(path: str) -> ui.tree:
    """Build the HDF5 tree with checkboxes only on group nodes."""
    ui.label("Structure").classes("text-subtitle2 p-2 pb-0")

    tree_data: list[dict[str, Any]] = []
    if os.path.isfile(path):
        with h5py.File(path, "r") as h5file:
            tree_data = build_tree(h5file)

    group_paths = _prepare_group_tree(tree_data)
    tick_keys_by_group = _collect_group_tick_keys(tree_data)
    selectable_group_paths = list(tick_keys_by_group)
    selected = [
        group_path
        for group_path in app.storage.user.get("export_selected_groups", [])
        if group_path in selectable_group_paths
    ]
    app.storage.user["export_available_groups"] = group_paths
    app.storage.user["export_selectable_groups"] = selectable_group_paths
    app.storage.user["export_tick_keys_by_group"] = tick_keys_by_group
    app.storage.user["export_selected_groups"] = selected

    tree = ui.tree(
        tree_data,
        label_key="label",
        node_key="id",
        tick_strategy="leaf",
        on_tick=_on_tree_tick,
    ).classes("w-full h-full overflow-auto")
    if selected:
        tree.tick(_tick_keys_for_groups(selected, tick_keys_by_group))
    return tree


def _prepare_group_tree(nodes: list[dict[str, Any]]) -> list[str]:
    """Hide dataset tick controls while preserving parent indeterminate states."""
    group_paths: list[str] = []
    for node in nodes:
        if node.get("type") == "group":
            group_paths.append(node["id"])
            children = node.get("children", [])
            group_paths.extend(_prepare_group_tree(children))
        else:
            # This hides the dataset checkbox while keeping the node available
            # as an internal tick key for QTree's parent aggregation.
            node["tickStrategy"] = "none"
    return group_paths


def _collect_group_tick_keys(nodes: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Map exportable groups to their direct QTree tick keys."""
    tick_keys: dict[str, list[str]] = {}
    for node in nodes:
        if node.get("type") != "group":
            continue
        children = node.get("children", [])
        direct_dataset_keys = [
            child["id"] for child in children if child.get("type") == "dataset"
        ]
        if direct_dataset_keys:
            tick_keys[node["id"]] = direct_dataset_keys
        elif not children:
            # Empty groups are still valid group selections.
            tick_keys[node["id"]] = [node["id"]]
        tick_keys.update(_collect_group_tick_keys(children))
    return tick_keys


def _tick_keys_for_groups(
    group_paths: list[str], tick_keys_by_group: dict[str, list[str]]
) -> list[str]:
    """Convert application group selections into QTree tick keys."""
    return [
        tick_key
        for group_path in group_paths
        for tick_key in tick_keys_by_group.get(group_path, [])
    ]


def _on_tree_tick(event: Any) -> None:
    """Store only ticked group paths and refresh the dependent panels."""
    ticked = set(event.value or [])
    tick_keys_by_group = app.storage.user.get("export_tick_keys_by_group", {})
    app.storage.user["export_selected_groups"] = [
        group_path
        for group_path, tick_keys in tick_keys_by_group.items()
        if any(tick_key in ticked for tick_key in tick_keys)
    ]
    _refresh_export_panels()


@ui.refreshable
def _build_selected_groups_panel(tree: ui.tree) -> None:
    """Show selected groups and bulk selection controls."""
    selected = app.storage.user.get("export_selected_groups", [])
    available = app.storage.user.get("export_available_groups", [])

    with ui.row().classes("w-full items-center justify-between"):
        ui.label("Selected groups").classes("text-subtitle1")
        with ui.row().classes("gap-2"):
            ui.button(
                "Select all",
                icon="select_all",
                on_click=lambda: _select_all_groups(tree),
            ).props("flat dense")
            ui.button(
                "Clear",
                icon="clear_all",
                on_click=lambda: _clear_selected_groups(tree),
            ).props("flat dense")

    if not selected:
        ui.label("Select one or more groups from the tree.").classes(
            "text-grey text-sm"
        )
        return

    ui.label(f"{len(selected)} group(s) selected").classes("text-caption")
    with ui.scroll_area().classes("w-full max-h-28"):
        for group_path in selected:
            ui.chip(
                group_path,
                icon="folder",
                removable=True,
                on_value_change=lambda _event, path=group_path: _remove_group(
                    tree, path
                ),
            )

    if not available:
        ui.label("The file contains no groups.").classes("text-grey text-sm")


@ui.refreshable
def _build_config_export_panel() -> None:
    """Build export controls that react to the selected mode and format."""
    selected = app.storage.user.get("export_selected_groups", [])
    mode = app.storage.user.get("export_mode", "side_by_side")
    output_format = app.storage.user.get("export_format", "csv")

    ui.label("Export configuration").classes("text-subtitle1")
    if not selected:
        ui.label("Export options will appear after selecting a group.").classes(
            "text-grey text-sm"
        )
        return

    with ui.column().classes("w-full gap-3"):
        ui.label("Format").classes("font-bold")
        ui.radio(
            {"csv": "CSV", "xlsx": "Excel (.xlsx)"},
            value=output_format,
            on_change=_on_format_change,
        ).props("inline")

        ui.label("Layout").classes("font-bold")
        layout_options = _available_layout_options(output_format)
        ui.radio(
            layout_options,
            value=mode,
            on_change=_on_mode_change,
        ).props("inline")
        with ui.row().classes("w-full gap-3 flex-wrap"):
            for mode_key, (title, description) in _EXPORT_MODES.items():
                is_disabled = mode_key == "sheets" and output_format == "csv"
                classes = "grow min-w-[220px]"
                if mode_key == mode:
                    classes += " border-2 border-primary bg-blue-1"
                elif is_disabled:
                    classes += " opacity-50"
                else:
                    classes += " cursor-pointer"

                card = ui.card().classes(classes)
                if not is_disabled:
                    card.on(
                        "click",
                        lambda _event, selected_mode=mode_key: _set_mode(
                            selected_mode
                        ),
                    )
                with card:
                    _build_layout_preview(mode_key)
                    with ui.row().classes("items-center gap-2 mt-2"):
                        ui.label(title).classes("font-bold")
                    ui.label(description).classes("text-sm text-grey")
                    if is_disabled:
                        ui.label("Available for Excel only").classes(
                            "text-xs text-negative"
                        )

        with ui.column().classes("w-full gap-2"):
            ui.label("Output").classes("font-bold")
            with ui.row().classes("w-full items-center gap-2"):
                ui.input(
                    "Output directory",
                    value=app.storage.user.get("export_output_dir", ""),
                ).bind_value(app.storage.user, "export_output_dir").classes("grow")
                ui.button(
                    icon="folder_open",
                    on_click=_pick_output_directory,
                ).props("flat round")

            if _needs_output_name(mode):
                ui.input(
                    "Output file name",
                    value=app.storage.user.get("export_output_name", "export.csv"),
                ).bind_value(
                    app.storage.user, "export_output_name"
                ).classes("w-full")
            else:
                ui.label(
                    "File names are generated from the selected group paths."
                ).classes("text-grey text-xs")

        ui.button(
            "Export",
            icon="file_download",
            on_click=_run_export,
        ).props("color=primary")


def _needs_output_name(mode: str) -> bool:
    """Return whether the selected export creates one named output file."""
    return mode in {"side_by_side", "sheets"}


def _default_output_name(source_path: str, output_format: str) -> str:
    """Return the default export filename derived from the source file."""
    suffix = ".xlsx" if output_format == "xlsx" else ".csv"
    if source_path == _NO_FILE:
        return f"export{suffix}"
    else:
        stem = Path(source_path).stem
    return f"{stem}-export{suffix}"


def _available_layout_options(output_format: str) -> dict[ExportMode, str]:
    """Return layout radio options valid for the selected output format."""
    return {
        mode_key: title
        for mode_key, (title, _) in _EXPORT_MODES.items()
        if output_format == "xlsx" or mode_key != "sheets"
    }


def _picker_start_directory(path: str) -> str:
    """Choose an existing directory from which the picker should start."""
    candidate = Path(path).expanduser() if path else Path.home()
    if candidate.is_dir():
        return str(candidate)
    if candidate.parent.is_dir():
        return str(candidate.parent)
    return str(Path.home())


async def _pick_output_directory() -> None:
    """Open a native or browser-based directory picker for export output."""
    current = app.storage.user.get("export_output_dir", "")
    start_directory = _picker_start_directory(current)

    if app.native.main_window:
        import webview

        paths = await app.native.main_window.create_file_dialog(
            dialog_type=webview.FileDialog.FOLDER,
            directory=start_directory,
        )
    else:
        picker = LocalFilePicker(
            directory=start_directory,
            select_directory=True,
        )
        paths = await picker

    if paths:
        app.storage.user["export_output_dir"] = str(paths[0])


def _build_layout_preview(mode: ExportMode) -> None:
    """Draw a compact visual preview for an export layout card."""
    preview_classes = "w-full h-20 rounded border border-grey-4 bg-grey-1 p-2"

    if mode == "side_by_side":
        with ui.column().classes(preview_classes + " gap-1"):
            with ui.row().classes("w-full gap-1"):
                for column in ("A", "B", "C"):
                    ui.label(column).classes(
                        "grow text-center text-xs font-bold bg-blue-2"
                    )
            for _ in range(2):
                with ui.row().classes("w-full gap-1"):
                    for _ in range(3):
                        ui.label("...").classes(
                            "grow text-center text-xs bg-white"
                        )
        return

    if mode == "sheets":
        with ui.column().classes(preview_classes + " gap-1"):
            with ui.row().classes("items-center gap-1"):
                ui.icon("table_view", size="xs")
                ui.label("export.xlsx").classes("text-xs font-bold")
            with ui.row().classes("w-full gap-1"):
                for sheet in ("group_001", "group_002", "group_003"):
                    ui.label(sheet).classes(
                        "grow truncate text-center text-xs bg-green-2"
                    )
            ui.label("One sheet per group").classes("text-xs text-grey")
        return

    with ui.row().classes(preview_classes + " items-center justify-around"):
        for filename in ("group_001", "group_002", "group_003"):
            with ui.column().classes("items-center gap-0"):
                ui.icon("description", size="sm")
                ui.label(filename).classes("text-[10px] truncate")


def _on_mode_change(event: Any) -> None:
    """Update the export mode selected by the layout radio group."""
    _set_mode(event.value)


def _on_format_change(event: Any) -> None:
    """Update the format and keep the selected mode valid."""
    output_format = event.value
    previous_format = app.storage.user.get("export_format", "csv")
    previous_name = app.storage.user.get("export_output_name", "")
    app.storage.user["export_format"] = output_format
    source_path = app.storage.user.get("h5_path", _NO_FILE)
    if previous_name == _default_output_name(source_path, previous_format):
        app.storage.user["export_output_name"] = _default_output_name(
            source_path, output_format
        )
    if output_format == "csv" and app.storage.user.get("export_mode") == "sheets":
        app.storage.user["export_mode"] = "side_by_side"
        ui.notify("The sheets layout is only available for Excel.", type="info")
    _build_config_export_panel.refresh()


def _set_mode(mode: ExportMode) -> None:
    """Set the export mode from a layout card."""
    if mode == "sheets" and app.storage.user.get("export_format") == "csv":
        return
    app.storage.user["export_mode"] = mode
    _build_config_export_panel.refresh()


def _select_all_groups(tree: ui.tree) -> None:
    """Tick every group in the current HDF5 tree."""
    selected = list(app.storage.user.get("export_selectable_groups", []))
    app.storage.user["export_selected_groups"] = selected
    tree.tick(
        _tick_keys_for_groups(
            selected,
            app.storage.user.get("export_tick_keys_by_group", {}),
        )
    )
    _refresh_export_panels()


def _clear_selected_groups(tree: ui.tree) -> None:
    """Untick every group in the current HDF5 tree."""
    app.storage.user["export_selected_groups"] = []
    tree.untick()
    _refresh_export_panels()


def _remove_group(tree: ui.tree, group_path: str) -> None:
    """Remove one group from the selection and untick it in the tree."""
    selected = [
        path
        for path in app.storage.user.get("export_selected_groups", [])
        if path != group_path
    ]
    app.storage.user["export_selected_groups"] = selected
    tree.untick(
        app.storage.user.get("export_tick_keys_by_group", {}).get(group_path, [])
    )
    _refresh_export_panels()


def _refresh_export_panels() -> None:
    """Refresh panels whose content depends on tree selection."""
    _build_selected_groups_panel.refresh()
    _build_config_export_panel.refresh()


async def _run_export() -> None:
    """Execute the configured export and notify the user of its result."""
    source_path = app.storage.user.get("h5_path", _NO_FILE)
    selected = app.storage.user.get("export_selected_groups", [])
    output_dir = app.storage.user.get("export_output_dir", "").strip()
    mode = app.storage.user.get("export_mode", "side_by_side")
    output_format = app.storage.user.get("export_format", "csv")

    if not selected:
        ui.notify("Select at least one group before exporting.", type="warning")
        return
    if not output_dir:
        ui.notify("Choose an output directory.", type="warning")
        return
    if not os.path.isfile(source_path):
        ui.notify("The selected HDF5 file is no longer available.", type="negative")
        return

    try:
        with h5py.File(source_path, "r") as h5file:
            if output_format == "csv":
                created = export_csv(
                    h5file,
                    selected,
                    mode=mode,
                    output_dir=output_dir,
                    output_name=_normalise_output_name(
                        app.storage.user.get("export_output_name", "export.csv"),
                        ".csv",
                    ),
                )
            else:
                created = export_xlsx(
                    h5file,
                    selected,
                    mode=mode,
                    output_dir=output_dir,
                    workbook_name=_normalise_output_name(
                        app.storage.user.get("export_output_name", "export.xlsx"),
                        ".xlsx",
                    ),
                )
    except (OSError, KeyError, NotImplementedError, ValueError) as exc:
        ui.notify(f"Export failed: {exc}", type="negative")
        return

    if created:
        ui.notify(f"Exported {len(created)} file(s) to {output_dir}.", type="positive")
    else:
        ui.notify(
            "No files were created; selected groups contain no datasets.",
            type="warning",
        )


def _normalise_output_name(name: str, suffix: str) -> str:
    """Keep an output name inside the output directory and add its suffix."""
    filename = Path(name.strip()).name
    if filename in {"", ".", ".."}:
        filename = f"export{suffix}"
    if Path(filename).suffix.lower() != suffix:
        filename = f"{filename}{suffix}"
    return filename
