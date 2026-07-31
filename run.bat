@echo off
call conda activate hdf5_manager || (
    echo Environment 'hdf5_manager' not found.
    echo Run: conda env create -f environment.yml
    pause
    exit /b 1
)
python -m hdf5_manager
pause
