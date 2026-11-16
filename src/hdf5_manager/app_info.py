"""Application metadata shared by the GUI and the packaging scripts.

Kept free of GUI imports so it can be used from the command line, from the
About dialog and from any packaging script.
"""

from __future__ import annotations

from hdf5_manager import __version__

APP_NAME = "HDF5 Manager"
DESCRIPTION = "HDF5 file viewer, editor, merger and exporter"
AUTHOR = "David Ibarra"
INSTITUTION = "Nanomol Group (ICMAB-CSIC)"
LICENSE_NAME = "MIT"
REPOSITORY_URL = "https://github.com/davidil98/HDF5-Manager"
# Institutional contact address shown in the About dialog. Leave empty to
# hide the contact row.
CONTACT_EMAIL = ""


def app_version() -> str:
    """Return the version shown in the About dialog.

    ``__version__`` is the single source of truth because it is the only one
    that survives inside a PyInstaller one-file bundle, where distribution
    metadata is not always available. Keep it in sync with ``pyproject.toml``
    and the git tag: the release workflow fails when the three disagree.
    """
    return __version__
