@echo off
REM ***********************************************
REM * Batch Script to Check for Python & Pip      *
REM * and install requirements from requirements.txt *
REM ***********************************************

REM Check if Python is installed by querying its version
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python is not installed.
    echo Installing Python 3.12 using winget...
    winget install Python.Python.3.12
    REM After installation, pause briefly to let changes settle
    timeout /t 10 >nul
) ELSE (
    echo Python is installed.
)

REM Now check if pip is available
pip --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Pip is not found.
    echo Attempting to install/upgrade pip using Python's ensurepip...
    python -m ensurepip --upgrade
    IF ERRORLEVEL 1 (
        echo Failed to install pip. Please install pip manually.
        goto End
    ) ELSE (
        echo Pip has been installed/upgraded successfully.
    )
) ELSE (
    echo Pip is installed.
)

REM Optionally check if requirements.txt exists before attempting installation
IF NOT EXIST requirements.txt (
    echo requirements.txt not found. Skipping pip install.
    goto End
)

echo Installing Python packages from requirements.txt...
pip install -r requirements.txt

:End
echo Script complete.
pause
