"""Tests for shared file-picker helpers."""

from __future__ import annotations

from hdf5_manager.web_gui.general import picker_start_directory


def test_picker_start_directory_uses_existing_file_parent(tmp_path) -> None:
    """A non-existing file path should start from its existing parent."""
    output = tmp_path / "nested" / "result.h5"
    assert picker_start_directory(str(output)) == str(tmp_path)


def test_picker_start_directory_preserves_existing_directory(tmp_path) -> None:
    """An existing directory should remain the dialog start location."""
    assert picker_start_directory(str(tmp_path)) == str(tmp_path)
