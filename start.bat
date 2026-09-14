@echo off
REM ══════════════════════════════════════════════════════════════════════
REM  start.bat — Jalankan SEMUA service sekaligus
REM  Hirunaza's Library Information System
REM
REM    - Django  (web utama)  : http://127.0.0.1:8000
REM    - FastAPI (REST API)   : http://127.0.0.1:8001/docs
REM    - Google Chrome dibuka otomatis
REM
REM  Pemakaian:
REM    start.bat              - jalankan semua + buka Chrome
REM    start.bat nobrowser    - jalankan semua TANPA membuka browser
REM
REM  Port & host dibaca dari file .env
REM ══════════════════════════════════════════════════════════════════════
setlocal EnableExtensions EnableDelayedExpansion
title Hirunaza's Library - Launcher
cd /d "%~dp0"

REM ── Cek virtual environment ──────────────────────────────────────────
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo ======================================================================
    echo   [X] Virtual environment .venv belum ada.
    echo ======================================================================
    echo   Jalankan dulu:  setup.bat
    echo.
    pause
    exit /b 1
)

REM ── Baca konfigurasi dari .env ───────────────────────────────────────
set "DJANGO_PORT=8000"
set "FASTAPI_HOST=127.0.0.1"
set "FASTAPI_PORT=8001"
if exist "%~dp0.env" (
    "%VENV_PY%" "%~dp0scripts\env_export.py" > "%TEMP%\hirunaza_env.bat" 2>nul
    if exist "%TEMP%\hirunaza_env.bat" (
        call "%TEMP%\hirunaza_env.bat"
        del /q "%TEMP%\hirunaza_env.bat" >nul 2>&1
    )
)

REM ── Argumen ──────────────────────────────────────────────────────────
set "OPEN_BROWSER=1"
if /i "%~1"=="nobrowser" set "OPEN_BROWSER=0"

echo ======================================================================
echo   HIRUNAZA'S LIBRARY INFORMATION SYSTEM
echo ======================================================================
echo   Web (Django)   : http://127.0.0.1:%DJANGO_PORT%
echo   REST API       : http://%FASTAPI_HOST%:%FASTAPI_PORT%/docs
echo   Panel admin    : http://127.0.0.1:%DJANGO_PORT%/admin/
echo ----------------------------------------------------------------------
echo   Menutup jendela server = mematikan service tersebut.
echo   Untuk mematikan semuanya sekaligus: stop.bat
echo ======================================================================
echo.

REM ── Cek apakah port sudah terpakai (hindari server ganda) ────────────
set "DJANGO_RUNNING=0"
set "FASTAPI_RUNNING=0"
netstat -ano | findstr /r /c:":%DJANGO_PORT% .*LISTENING" >nul 2>&1 && set "DJANGO_RUNNING=1"
netstat -ano | findstr /r /c:":%FASTAPI_PORT% .*LISTENING" >nul 2>&1 && set "FASTAPI_RUNNING=1"

if "!DJANGO_RUNNING!"=="1" (
    echo [!] Port %DJANGO_PORT% sudah dipakai - Django TIDAK dijalankan ulang.
    echo     Bila itu server lama dengan kode usang, tutup lewat stop.bat dulu.
    echo.
) else (
    echo [1/2] Menjalankan Django di port %DJANGO_PORT% ...
    start "Hirunaza Django :%DJANGO_PORT%" cmd /k ""%VENV_PY%" manage.py runserver 127.0.0.1:%DJANGO_PORT%"
)

if "!FASTAPI_RUNNING!"=="1" (
    echo [!] Port %FASTAPI_PORT% sudah dipakai - FastAPI TIDAK dijalankan ulang.
    echo.
) else (
    echo [2/2] Menjalankan FastAPI di port %FASTAPI_PORT% ...
    start "Hirunaza FastAPI :%FASTAPI_PORT%" cmd /k ""%VENV_PY%" -m uvicorn api.main:app --host %FASTAPI_HOST% --port %FASTAPI_PORT%"
)

REM ── Tunggu sampai Django siap (maks ~60 detik) ───────────────────────
echo.
echo Menunggu server siap ...
set /a TRIES=0
:waitloop
set /a TRIES+=1
curl -s -o nul -m 2 "http://127.0.0.1:%DJANGO_PORT%/login/" >nul 2>&1
if !errorlevel! EQU 0 goto ready
if !TRIES! GEQ 30 goto timeout
ping -n 2 127.0.0.1 >nul
goto waitloop

:timeout
echo [!] Server belum merespons setelah ~60 detik.
echo     Periksa jendela "Hirunaza Django" untuk melihat pesan error.
goto finish

:ready
echo [OK] Django siap di http://127.0.0.1:%DJANGO_PORT%
curl -s -o nul -m 2 "http://%FASTAPI_HOST%:%FASTAPI_PORT%/api/health" >nul 2>&1
if !errorlevel! EQU 0 (
    echo [OK] FastAPI siap di http://%FASTAPI_HOST%:%FASTAPI_PORT%/docs
) else (
    echo [!] FastAPI belum merespons - cek jendela "Hirunaza FastAPI".
)

REM ── Buka Chrome ──────────────────────────────────────────────────────
if "%OPEN_BROWSER%"=="1" (
    echo.
    echo Membuka Google Chrome ...
    set "CHROME_EXE="
    if exist "!ProgramFiles!\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=!ProgramFiles!\Google\Chrome\Application\chrome.exe"
    if not defined CHROME_EXE if exist "!ProgramFiles(x86)!\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=!ProgramFiles(x86)!\Google\Chrome\Application\chrome.exe"
    if not defined CHROME_EXE if exist "!LOCALAPPDATA!\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=!LOCALAPPDATA!\Google\Chrome\Application\chrome.exe"

    if defined CHROME_EXE (
        start "" "!CHROME_EXE!" "http://127.0.0.1:%DJANGO_PORT%/"
    ) else (
        echo [!] Chrome tidak ditemukan di lokasi standar - memakai browser default.
        start "" "http://127.0.0.1:%DJANGO_PORT%/"
    )
) else (
    echo.
    echo Mode nobrowser: browser tidak dibuka.
    echo   Buka manual: http://127.0.0.1:%DJANGO_PORT%
)

:finish
echo.
echo ======================================================================
echo   Akun terdaftar di database:
"%VENV_PY%" "%~dp0scripts\list_accounts.py"
echo ======================================================================
if "%OPEN_BROWSER%"=="0" (
    echo Tekan tombol apa saja untuk menutup jendela launcher ini.
    pause >nul
)
endlocal
exit /b 0
