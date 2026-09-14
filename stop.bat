@echo off
REM ══════════════════════════════════════════════════════════════════════
REM  stop.bat — Matikan semua service Hirunaza's Library
REM  Menutup proses yang menahan port Django (mis. 8000) & FastAPI (mis. 8001)
REM ══════════════════════════════════════════════════════════════════════
setlocal EnableExtensions EnableDelayedExpansion
title Stop - Hirunaza Library
cd /d "%~dp0"

set "VENV_PY=%~dp0.venv\Scripts\python.exe"

REM ── Baca port dari .env bila tersedia ────────────────────────────────
set "DJANGO_PORT=8000"
set "FASTAPI_PORT=8001"
if exist "%VENV_PY%" if exist "%~dp0.env" (
    "%VENV_PY%" "%~dp0scripts\env_export.py" > "%TEMP%\hirunaza_env.bat" 2>nul
    if exist "%TEMP%\hirunaza_env.bat" (
        call "%TEMP%\hirunaza_env.bat"
        del /q "%TEMP%\hirunaza_env.bat" >nul 2>&1
    )
)

echo ======================================================================
echo   Menghentikan service pada port %DJANGO_PORT% (Django) ^& %FASTAPI_PORT% (FastAPI)
echo ======================================================================
echo.

set "KETEMU=0"
for %%P in (%DJANGO_PORT% %FASTAPI_PORT%) do (
    for /f "tokens=5" %%I in ('netstat -ano ^| findstr /r /c:":%%P .*LISTENING"') do (
        set "KETEMU=1"
        echo   - Port %%P : menghentikan PID %%I
        taskkill /F /PID %%I >nul 2>&1
    )
)

if "!KETEMU!"=="0" (
    echo   Tidak ada service yang berjalan di port %DJANGO_PORT% / %FASTAPI_PORT%.
) else (
    echo.
    echo   [OK] Service dihentikan.
)

REM ── Tutup juga jendela launcher yang dibuka start.bat ─────────────────
REM Tanpa langkah ini, jendela "Hirunaza Django/FastAPI" tetap terbuka
REM dan lama-lama menumpuk walau servernya sudah mati.
echo.
echo   Menutup jendela launcher (bila ada) ...
taskkill /F /IM cmd.exe /FI "WINDOWTITLE eq Hirunaza*" >nul 2>&1
taskkill /F /IM cmd.exe /FI "WINDOWTITLE eq Administrator: Hirunaza*" >nul 2>&1
echo   [OK] Selesai.

echo.
echo Tekan tombol apa saja untuk menutup.
pause >nul
endlocal
exit /b 0
