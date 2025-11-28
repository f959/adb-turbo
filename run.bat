@echo off
REM ============================================
REM adb-turbo - Launch Script (Windows)
REM ============================================

setlocal enabledelayedexpansion

REM Configuration
set PORT=8765
set HOST=localhost
set URL=http://%HOST%:%PORT%

REM Colors (Windows 10+)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "PURPLE=[95m"
set "CYAN=[96m"
set "NC=[0m"

REM ============================================
REM Print Banner
REM ============================================
:print_banner
echo %PURPLE%
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║        adb-turbo                                             ║
echo ║        Friendly Android Performance Tool                     ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo %NC%
goto :eof

REM ============================================
REM Check and Install UV
REM ============================================
:check_uv
echo %CYAN%Checking for UV...%NC%

where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo %GREEN%✓ UV is installed%NC%
    uv --version
    goto :eof
) else (
    echo %YELLOW%UV not found. Installing UV...%NC%
    call :install_uv
)
goto :eof

:install_uv
echo %CYAN%Installing UV via PowerShell...%NC%
powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"

where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo %GREEN%✓ UV installed successfully%NC%
) else (
    echo %RED%✗ Failed to install UV. Please install manually:%NC%
    echo %YELLOW%  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"%NC%
    exit /b 1
)
goto :eof

REM ============================================
REM Check Python
REM ============================================
:check_python
echo %CYAN%Checking Python version...%NC%

where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo %GREEN%✓ Python !PYTHON_VERSION! found%NC%
) else (
    echo %RED%✗ Python not found%NC%
    echo %YELLOW%Please install Python 3.10 or higher from https://www.python.org/%NC%
    exit /b 1
)
goto :eof

REM ============================================
REM Check ADB
REM ============================================
:check_adb
echo %CYAN%Checking for ADB...%NC%

where adb >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('adb version 2^>^&1 ^| findstr /r "."') do (
        echo %GREEN%✓ ADB found: %%i%NC%
        goto :adb_found
    )
    :adb_found
) else (
    echo %YELLOW%⚠ ADB not found in PATH%NC%
    echo %YELLOW%The application will still run, but you'll need to install ADB to use it.%NC%
    echo %YELLOW%Installation instructions will be shown in the web interface.%NC%
)
goto :eof

REM ============================================
REM Install Dependencies
REM ============================================
:install_dependencies
echo %CYAN%Installing dependencies with UV...%NC%

uv sync --no-install-project
if %errorlevel% equ 0 (
    echo %GREEN%✓ Dependencies installed successfully%NC%
) else (
    echo %RED%✗ Failed to install dependencies%NC%
    exit /b 1
)
goto :eof

REM ============================================
REM Open Browser
REM ============================================
:open_browser
echo %CYAN%Opening browser...%NC%

timeout /t 2 /nobreak >nul
start "" "%URL%"
goto :eof

REM ============================================
REM Start Server
REM ============================================
:start_server
echo %CYAN%Starting Flask server...%NC%
echo.
echo %GREEN%╔══════════════════════════════════════════════════════════════╗%NC%
echo %GREEN%║                                                              ║%NC%
echo %GREEN%║  🚀 Server running at: %BLUE%%URL%%GREEN%                      ║%NC%
echo %GREEN%║                                                              ║%NC%
echo %GREEN%║  📱 Make sure:                                               ║%NC%
echo %GREEN%║     • ADB is installed and in your PATH                      ║%NC%
echo %GREEN%║     • USB debugging is enabled on your device                ║%NC%
echo %GREEN%║     • Your device is connected via USB                       ║%NC%
echo %GREEN%║                                                              ║%NC%
echo %GREEN%║  Press Ctrl+C to stop the server                             ║%NC%
echo %GREEN%║                                                              ║%NC%
echo %GREEN%╚══════════════════════════════════════════════════════════════╝%NC%
echo.

REM Open browser in background
start /b cmd /c call :open_browser

REM Start the Flask app with UV
uv run python app.py
goto :eof

REM ============================================
REM Main Execution
REM ============================================
:main
call :print_banner

echo %CYAN%Starting adb-turbo...%NC%
echo.

REM Check prerequisites
call :check_python
if %errorlevel% neq 0 exit /b 1

call :check_uv
if %errorlevel% neq 0 exit /b 1

call :check_adb

echo.

REM Install dependencies
call :install_dependencies
if %errorlevel% neq 0 exit /b 1

echo.

REM Start server
call :start_server

goto :eof

REM Run main function
call :main

