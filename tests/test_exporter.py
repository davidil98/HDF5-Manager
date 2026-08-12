"""Tests for exporter UI data preparation helpers."""

from __future__ import annotations

from pathlib import Path

from hdf5_manager.web_gui.exporter import (
    _available_layout_options,
    _collect_group_tick_keys,
    _default_output_name,
    _normalise_output_name,
    _picker_start_directory,
    _prepare_group_tree,
)


def test_prepare_group_tree_only_disables_dataset_ticks() -> None:
    """Datasets hide their ticks while groups remain part of the tick model."""
    nodes = [
        {
            "id": "/run",
            "type": "group",
            "children": [
                {"id": "/run/voltage", "type": "dataset", "children": []},
                {
                    "id": "/run/curve",
                    "type": "group",
                    "children": [
                        {
                            "id": "/run/curve/current",
                            "type": "dataset",
                            "children": [],
                        }
                    ],
                },
            ],
        }
    ]

    groups = _prepare_group_tree(nodes)

    assert groups == ["/run", "/run/curve"]
    assert "noTick" not in nodes[0]
    assert "tickStrategy" not in nodes[0]
    assert nodes[0]["children"][0]["tickStrategy"] == "none"
    terminal_group = nodes[0]["children"][1]
    assert "tickStrategy" not in terminal_group
    assert terminal_group["children"][0]["tickStrategy"] == "none"
    assert _collect_group_tick_keys(nodes) == {
        "/run": ["/run/voltage"],
        "/run/curve": ["/run/curve/current"],
    }


def test_normalise_output_name_keeps_only_a_safe_filename() -> None:
    """Output names cannot escape the configured output directory."""
    assert _normalise_output_name("/tmp/report", ".xlsx") == "report.xlsx"
    assert _normalise_output_name("report.CSV", ".csv") == "report.CSV"
    assert _normalise_output_name("", ".csv") == "export.csv"


def test_default_output_name_uses_source_stem_and_format() -> None:
    """The default output name follows the source file and selected format."""
    assert _default_output_name("/tmp/measurement.h5", "csv") == (
        "measurement-export.csv"
    )
    assert _default_output_name("/tmp/measurement.h5", "xlsx") == (
        "measurement-export.xlsx"
    )
    assert _default_output_name("No file selected", "csv") == "export.csv"


def test_available_layout_options_filters_excel_only_layouts() -> None:
    """CSV should not expose the Excel-only sheets layout as a radio option."""
    assert set(_available_layout_options("csv")) == {
        "side_by_side",
        "per_group",
    }
    assert set(_available_layout_options("xlsx")) == {
        "side_by_side",
        "sheets",
        "per_group",
    }


def test_picker_start_directory_prefers_existing_directory(tmp_path: Path) -> None:
    """The output picker starts at the current directory or its parent."""
    output_dir = tmp_path / "exports"
    output_dir.mkdir()
    assert _picker_start_directory(str(output_dir)) == str(output_dir)
    assert (
        _picker_start_directory(str(output_dir / "report.csv")) == str(output_dir)
    )
