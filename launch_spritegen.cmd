@echo off
setlocal

cd /d "%~dp0"

if "%~1"=="--check" (
    py -3 -c "import sys; print(sys.version)"
    exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher "py" was not found.
    echo Install Python 3.11 or newer from https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Failed to create .venv.
        pause
        exit /b 1
    )
)

echo Installing or updating spritegen desktop dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to update pip.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -e ".[gui]"
if errorlevel 1 (
    echo Failed to install spritegen.
    pause
    exit /b 1
)

echo Starting spritegen...
start "" ".venv\Scripts\pythonw.exe" -m spritegen.desktop
exit /b 0
