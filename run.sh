#!/bin/bash
# HDF5 Manager — Linux/macOS launcher for end users.
# Activates the conda environment and runs the application.

set -e

# Resolve script directory so this works regardless of CWD.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Locate conda installation.
if [ -z "${CONDA_EXE:-}" ]; then
    if command -v conda &> /dev/null; then
        CONDA_BASE="$(conda info --base 2>/dev/null)"
    else
        echo "Error: conda not found. Install Miniconda or Anaconda first." >&2
        exit 1
    fi
else
    CONDA_BASE="$(dirname "$(dirname "$CONDA_EXE")")"
fi

# Source conda's shell hooks so `conda activate` works in this script.
# shellcheck disable=SC1091
source "$CONDA_BASE/etc/profile.d/conda.sh"

# Activate the project environment (created via environment.yml).
if ! conda activate hdf5_manager 2>/dev/null; then
    echo "Error: conda environment 'hdf5_manager' not found." >&2
    echo "Create it with: conda env create -f $SCRIPT_DIR/environment.yml" >&2
    exit 1
fi

# Launch the production profile via the console script entry point.
hdf5-manager --mode auto
