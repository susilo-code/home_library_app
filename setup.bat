@echo off
REM ══════════════════════════════════════════════════════════════════════
REM  setup.bat — Persiapan sekali jalan untuk PC baru
REM  Hirunaza's Library Information System
REM
REM  PENTING: PC baru TIDAK wajib sudah punya Python.
REM  Urutan yang dicoba:
REM    1. Python 3.11+ yang sudah ada di PC
REM    2. uv (bila ada)  -> uv mengunduh Python 3.11 sendiri
REM    3. Pasang uv otomatis (winget, lalu PowerShell/astral.sh)
REM    Bila semuanya gagal, script berhenti dengan petunjuk instalasi Python.
REM
REM  Yang dilakukan:
REM    1. Siapkan Python (atau lewat uv)
REM    2. Buat virtual environment .venv
REM    3. Install dependency dari requirements.txt
REM    4. Buat file .env (dari .env.example + SECRET_KEY acak)
REM    5. Migrasi database
REM    6. (opsional) Build Tailwind CSS bila Node.js tersedia
REM    7. (opsional) Isi data contoh & buat akun admin
REM
REM  Syarat: koneksi internet (untuk mengunduh Python/dependency).
REM  Pemakaian:  setup.bat
REM ══════════════════════════════════════════════════════════════════════
setlocal EnableExtensions EnableDelayedExpansion
title Setup - Hirunaza's Library
cd /d "%~dp0"

echo ======================================================================
echo   SETUP HIRUNAZA'S LIBRARY INFORMATION SYSTEM
echo ======================================================================
echo.

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "HAS_UV="
set "PY_CMD="

REM ── 1. Cari Python 3.11+ yang sudah terpasang ────────────────────────
for %%C in ("py -3.11" "py -3.12" "py -3.13" "py -3" "python") do (
    if not defined PY_CMD (
        %%~C -c "import sys;raise SystemExit(0 if sys.version_info[:2]>=(3,11) else 1)" >nul 2>&1 && set "PY_CMD=%%~C"
    )
)

if defined PY_CMD (
    for /f "tokens=2" %%V in ('%PY_CMD% --version 2^>^&1') do set "PY_VER=%%V"
    echo [1/7] Python ditemukan: !PY_VER!  ^(perintah: %PY_CMD%^)
) else (
    echo [1/7] Python 3.11+ tidak ditemukan di PC ini.
    echo       Mencari uv ^(uv dapat mengunduh Python sendiri^) ...
    call :pastikan_uv
    if not defined HAS_UV (
        echo.
        echo [X] Tidak ada Python maupun uv, dan pemasangan uv otomatis gagal.
        echo.
        echo     Pilihan termudah:
        echo       1. Install Python 3.11 atau 3.12 dari https://www.python.org/downloads/
        echo          PENTING: centang "Add python.exe to PATH" saat instalasi.
        echo       2. Atau install uv dari https://docs.astral.sh/uv/ lalu ulangi setup.bat
        echo.
        echo     Setelah itu jalankan setup.bat lagi.
        pause
        exit /b 1
    )
    echo       uv tersedia - Python 3.11 akan diunduh otomatis oleh uv.
)

REM ── 2. Buat virtual environment ──────────────────────────────────────
if exist "%VENV_PY%" (
    echo [2/7] Virtual environment .venv sudah ada - dilewati
) else (
    where uv >nul 2>&1 && set "HAS_UV=1"
    if defined HAS_UV (
        echo [2/7] Membuat .venv dengan uv - Python 3.11 ^(diunduh bila belum ada^)
        uv venv --python 3.11 .venv
    ) else (
        echo [2/7] Membuat .venv dengan venv bawaan Python
        %PY_CMD% -m venv .venv
    )
    if not exist "%VENV_PY%" (
        echo [X] Gagal membuat virtual environment.
        pause
        exit /b 1
    )
)

REM ── 3. Install dependency ────────────────────────────────────────────
echo [3/7] Memasang dependency dari requirements.txt ...
where uv >nul 2>&1 && set "HAS_UV=1"
if defined HAS_UV (
    uv pip install --python "%VENV_PY%" -r requirements.txt
) else (
    "%VENV_PY%" -m pip install --upgrade pip --quiet
    "%VENV_PY%" -m pip install -r requirements.txt
)
if errorlevel 1 (
    echo       Cara pertama gagal - mencoba cara kedua ...
    if defined HAS_UV (
        "%VENV_PY%" -m ensurepip --upgrade >nul 2>&1
        "%VENV_PY%" -m pip install -r requirements.txt
    ) else (
        uv pip install --python "%VENV_PY%" -r requirements.txt
    )
)
"%VENV_PY%" -c "import django, fastapi" >nul 2>&1
if errorlevel 1 (
    echo [X] Instalasi dependency gagal. Periksa koneksi internet lalu ulangi setup.bat
    pause
    exit /b 1
)

REM ── 4. Buat .env ─────────────────────────────────────────────────────
echo [4/7] Menyiapkan file .env ...
"%VENV_PY%" scripts\init_env.py

REM ── 5. Migrasi database ──────────────────────────────────────────────
echo [5/7] Menjalankan migrasi database ...
"%VENV_PY%" manage.py migrate
if errorlevel 1 (
    echo [X] Migrasi gagal. Periksa pengaturan DB_ENGINE di file .env
    pause
    exit /b 1
)

REM ── 6. Tailwind CSS (opsional, butuh Node.js) ────────────────────────
echo [6/7] Tailwind CSS ...
where npm >nul 2>&1
if !errorlevel! EQU 0 (
    echo       Node.js terdeteksi - memasang ^& membangun CSS ...
    call npm install --silent
    call npm run build
    echo       CSS lokal diperbarui: static\css\output.css
) else (
    echo       Node.js tidak ditemukan - DILEWATI.
    echo       Tidak masalah: static\css\output.css sudah ikut ter-commit
    echo       dan tampilan tetap berjalan.
)

REM ── 7. Data contoh & akun admin (opsional) ───────────────────────────
echo [7/7] Data awal
set "ISI_DATA="
set /p "ISI_DATA=      Isi data contoh (5 user + buku)? [y/N]: "
if /i "!ISI_DATA!"=="y" (
    "%VENV_PY%" manage.py seed_data --users 5 --books-per-user 8
) else (
    echo       Dilewati. Jalankan nanti bila perlu:
    echo         .venv\Scripts\python.exe manage.py seed_data
)

set "BUAT_ADMIN="
set /p "BUAT_ADMIN=      Buat akun admin sekarang (createsuperuser)? [y/N]: "
if /i "!BUAT_ADMIN!"=="y" "%VENV_PY%" manage.py createsuperuser

echo.
echo ======================================================================
echo   SETUP SELESAI
echo ======================================================================
echo   Jalankan aplikasi dengan:  start.bat
echo   Login contoh (bila data contoh diisi): user1 / password123
echo   Untuk bisa mengelola pengguna, jadikan admin:
echo     .venv\Scripts\python.exe manage.py create_user --username user1 --superuser
echo   Panel admin: http://127.0.0.1:8000/admin/
echo ======================================================================
echo.
pause
exit /b 0


REM ══════════════════════════════════════════════════════════════════════
REM  Subrutin: pastikan uv tersedia (set HAS_UV=1 bila berhasil)
REM ══════════════════════════════════════════════════════════════════════
:pastikan_uv
where uv >nul 2>&1 && set "HAS_UV=1"
if defined HAS_UV (
    echo       uv sudah tersedia.
    exit /b 0
)
REM uv hasil pemasangan biasanya ada di %USERPROFILE%\.local\bin (belum masuk PATH)
if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    set "HAS_UV=1"
    echo       uv ditemukan di %USERPROFILE%\.local\bin
    exit /b 0
)

REM Cara 1: winget (Windows 10 versi baru / Windows 11)
where winget >nul 2>&1
if !errorlevel! EQU 0 (
    echo       Memasang uv lewat winget ...
    winget install --id astral-sh.uv -e --silent --accept-source-agreements --accept-package-agreements
    if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    where uv >nul 2>&1 && set "HAS_UV=1"
    if defined HAS_UV (
        echo       uv terpasang lewat winget.
        exit /b 0
    )
)

REM Cara 2: skrip resmi astral.sh lewat PowerShell
echo       Memasang uv lewat PowerShell ^(astral.sh^) ...
powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex" >nul 2>&1
if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>&1 && set "HAS_UV=1"
if defined HAS_UV (
    echo       uv terpasang lewat PowerShell.
    exit /b 0
)

REM Cara 3: unduh langsung arsip resmi dari GitHub Releases lalu ekstrak
echo       Mengunduh uv dari GitHub Releases ...
set "UV_TMP=%TEMP%\uv_setup_hirunaza"
if exist "%UV_TMP%" rmdir /s /q "%UV_TMP%"
mkdir "%UV_TMP%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy ByPass -Command "try { Invoke-WebRequest -Uri 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip' -OutFile '%UV_TMP%\uv.zip' -UseBasicParsing -TimeoutSec 120; Expand-Archive -Path '%UV_TMP%\uv.zip' -DestinationPath '%UV_TMP%' -Force } catch { exit 1 }" >nul 2>&1
if exist "%UV_TMP%\uv.exe" (
    mkdir "%USERPROFILE%\.local\bin" >nul 2>&1
    copy /y "%UV_TMP%\uv.exe" "%USERPROFILE%\.local\bin\uv.exe" >nul 2>&1
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    where uv >nul 2>&1 && set "HAS_UV=1"
    echo       uv terpasang dari GitHub Releases.
)
rmdir /s /q "%UV_TMP%" >nul 2>&1
exit /b 0
