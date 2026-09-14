@echo off
REM ══════════════════════════════════════════════════════════════════════
REM  setup.bat — Persiapan sekali jalan untuk PC baru
REM  Hirunaza's Library Information System
REM
REM  Yang dilakukan:
REM    1. Cek Python 3.11+
REM    2. Buat virtual environment .venv
REM    3. Install dependency dari requirements.txt
REM    4. Buat file .env (dari .env.example + SECRET_KEY acak)
REM    5. Migrasi database
REM    6. (opsional) Build Tailwind CSS bila Node.js tersedia
REM    7. (opsional) Isi data contoh & buat akun admin
REM
REM  Pemakaian:  setup.bat
REM ══════════════════════════════════════════════════════════════════════
setlocal EnableExtensions EnableDelayedExpansion
title Setup - Hirunaza's Library
cd /d "%~dp0"

echo ======================================================================
echo   SETUP HIRUNAZA'S LIBRARY INFORMATION SYSTEM
echo ======================================================================
echo.

REM ── 1. Cari Python 3.11+ ─────────────────────────────────────────────
set "PY_CMD="
py -3.11 --version >nul 2>&1 && set "PY_CMD=py -3.11"
if not defined PY_CMD ( py -3 --version >nul 2>&1 && set "PY_CMD=py -3" )
if not defined PY_CMD ( python --version >nul 2>&1 && set "PY_CMD=python" )
if not defined PY_CMD (
    echo [X] Python tidak ditemukan.
    echo     Install Python 3.11 atau 3.12 dari https://www.python.org/downloads/
    echo     PENTING: centang "Add python.exe to PATH" saat instalasi.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%V in ('%PY_CMD% --version 2^>^&1') do set "PY_VER=%%V"
echo [1/7] Python ditemukan: %PY_VER%  (perintah: %PY_CMD%)

REM ── 2. Buat virtual environment ──────────────────────────────────────
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    echo [2/7] Virtual environment .venv sudah ada - dilewati
) else (
    where uv >nul 2>&1
    if !errorlevel! EQU 0 (
        echo [2/7] Membuat .venv dengan uv -^> cepat
        uv venv .venv
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
"%VENV_PY%" -m pip install --upgrade pip --quiet
if errorlevel 1 (
    REM uv-venv tidak menyertakan pip; pasang lewat ensurepip
    "%VENV_PY%" -m ensurepip --upgrade >nul 2>&1
    "%VENV_PY%" -m pip install --upgrade pip --quiet >nul 2>&1
)
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [!] pip gagal. Mencoba lewat uv ...
    uv pip install --python "%VENV_PY%" -r requirements.txt
    if errorlevel 1 (
        echo [X] Instalasi dependency gagal. Periksa koneksi internet lalu ulangi setup.bat
        pause
        exit /b 1
    )
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
echo   Panel admin: http://127.0.0.1:8000/admin/
echo ======================================================================
echo.
pause
