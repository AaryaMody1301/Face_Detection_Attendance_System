@echo off
REM Face Detection Attendance System Launcher
REM This batch file launches the Face Detection Attendance System application.

echo Starting Face Detection Attendance System...

REM Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.7 or higher and try again.
    pause
    exit /b 1
)

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

REM Change to the script directory
cd /d "%SCRIPT_DIR%"

REM Run the application
python main.py
if %ERRORLEVEL% neq 0 (
    echo Application exited with error code: %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo Application closed.
pause
exit /b 0