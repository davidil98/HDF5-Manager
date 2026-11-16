"""Tests for the application metadata helpers."""

from __future__ import annotations

import re

from hdf5_manager import __version__, app_info


def test_app_version_is_semver_like() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", app_info.app_version())


def test_app_version_matches_module_constant() -> None:
    assert app_info.app_version() == __version__


def test_repository_url_is_https() -> None:
    assert app_info.REPOSITORY_URL.startswith("https://")


def test_contact_email_is_empty_or_looks_like_an_email() -> None:
    assert app_info.CONTACT_EMAIL == "" or "@" in app_info.CONTACT_EMAIL
