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
REM    7. OTOMATIS membuat akun superuser - bawaan admin / 123 - tanpa tanya-jawab
REM       Aman diulang: bila akun sudah ada, peran/status dipastikan dan sandi
REM       disetel ulang (tidak pernah gagal karena nama pengguna sudah dipakai).
REM    8. (opsional) Isi data contoh
REM
REM  Syarat: koneksi internet (untuk mengunduh Python/dependency).
REM
REM  Pemakaian:
REM    setup.bat                     -> akun superuser admin/123 langsung dibuat
REM    setup.bat /seed               -> sekalian isi 5 user + buku contoh (tanpa tanya)
REM    setup.bat /nopause            -> lewati semua "pause" (untuk otomatisasi/CI)
REM
REM  Variabel lingkungan yang dihormati:
REM    ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_EMAIL  -> ubah akun superuser
REM    SEED_DATA=1|0                                -> paksa isi / lewati data contoh
REM    SETUP_NO_PAUSE=1                             -> sama dengan /nopause
REM ══════════════════════════════════════════════════════════════════════
setlocal EnableExtensions EnableDelayedExpansion
title Setup - Hirunaza's Library
cd /d "%~dp0"

REM ── 0. Argumen opsional ───────────────────────────────────────────────
if /i "%~1"=="/seed" set "SEED_DATA=1"
if /i "%~1"=="/demo" set "SEED_DATA=1"
if /i "%~1"=="/nodemo" set "SEED_DATA=0"
if /i "%~1"=="/nopause" set "SETUP_NO_PAUSE=1"
if /i "%~2"=="/seed" set "SEED_DATA=1"
if /i "%~2"=="/demo" set "SEED_DATA=1"
if /i "%~2"=="/nodemo" set "SEED_DATA=0"
if /i "%~2"=="/nopause" set "SETUP_NO_PAUSE=1"

echo ======================================================================
echo   SETUP HIRUNAZA'S LIBRARY INFORMATION SYSTEM
echo ======================================================================
echo.

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "HAS_UV="
set "PY_CMD="
set "ADMIN_GAGAL="

REM ── 1. Cari Python 3.11+ yang sudah terpasang ────────────────────────
for %%C in ("py -3.11" "py -3.12" "py -3.13" "py -3" "python") do (
    if not defined PY_CMD (
        %%~C -c "import sys;raise SystemExit(0 if sys.version_info[:2]>=(3,11) else 1)" >nul 2>&1 && set "PY_CMD=%%~C"
    )
)

if defined PY_CMD (
    for /f "tokens=2" %%V in ('%PY_CMD% --version 2^>^&1') do set "PY_VER=%%V"
    echo [1/8] Python ditemukan: !PY_VER!  ^(perintah: %PY_CMD%^)
) else (
    echo [1/8] Python 3.11+ tidak ditemukan di PC ini.
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
        call :jeda
        exit /b 1
    )
    echo       uv tersedia - Python 3.11 akan diunduh otomatis oleh uv.
)

REM ── 2. Buat virtual environment ──────────────────────────────────────
if exist "%VENV_PY%" (
    echo [2/8] Virtual environment .venv sudah ada - dilewati
) else (
    where uv >nul 2>&1 && set "HAS_UV=1"
    if defined HAS_UV (
        echo [2/8] Membuat .venv dengan uv - Python 3.11 ^(diunduh bila belum ada^)
        uv venv --python 3.11 .venv
    ) else (
        echo [2/8] Membuat .venv dengan venv bawaan Python
        %PY_CMD% -m venv .venv
    )
    if not exist "%VENV_PY%" (
        echo [X] Gagal membuat virtual environment.
        call :jeda
        exit /b 1
    )
)

REM ── 3. Install dependency ────────────────────────────────────────────
echo [3/8] Memasang dependency dari requirements.txt ...
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
    call :jeda
    exit /b 1
)

REM ── 4. Buat .env ─────────────────────────────────────────────────────
echo [4/8] Menyiapkan file .env ...
"%VENV_PY%" scripts\init_env.py

REM ── 5. Migrasi database ──────────────────────────────────────────────
echo [5/8] Menjalankan migrasi database ...
"%VENV_PY%" manage.py migrate
if errorlevel 1 (
    echo [X] Migrasi gagal. Periksa pengaturan DB_ENGINE di file .env
    call :jeda
    exit /b 1
)

REM ── 6. Tailwind CSS (opsional, butuh Node.js) ────────────────────────
echo [6/8] Tailwind CSS ...
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

REM ── 7. Akun superuser (OTOMATIS, tanpa tanya-jawab) ──────────────────
echo [7/8] Menyiapkan akun superuser otomatis ...
if not defined ADMIN_USERNAME set "ADMIN_USERNAME=admin"
if not defined ADMIN_PASSWORD set "ADMIN_PASSWORD=123"
"%VENV_PY%" manage.py ensure_superuser
if errorlevel 1 (
    set "ADMIN_GAGAL=1"
    echo [X] Akun superuser gagal disiapkan otomatis.
    echo     Setelah setup selesai, jalankan manual:
    echo       .venv\Scripts\python.exe manage.py ensure_superuser
)

REM ── 8. Data contoh (opsional, tidak menggantung) ─────────────────────
echo [8/8] Data contoh
set "ISI_DATA="
if defined SEED_DATA (
    if "!SEED_DATA!"=="1" set "ISI_DATA=1"
    if "!SEED_DATA!"=="0" set "ISI_DATA=0"
    if /i "!SEED_DATA!"=="y" set "ISI_DATA=1"
    if /i "!SEED_DATA!"=="n" set "ISI_DATA=0"
)
if not defined ISI_DATA call :tanya_data
if "!ISI_DATA!"=="1" (
    "%VENV_PY%" manage.py seed_data --users 5 --books-per-user 8
) else (
    echo       Dilewati. Jalankan nanti bila perlu:
    echo         .venv\Scripts\python.exe manage.py seed_data
)

echo.
echo ======================================================================
echo   SETUP SELESAI
echo ======================================================================
echo   Jalankan aplikasi dengan:  start.bat
echo.
if defined ADMIN_GAGAL (
    echo   [!] Akun superuser BELUM dibuat. Jalankan:
    echo         .venv\Scripts\python.exe manage.py ensure_superuser
) else (
    echo   Akun superuser siap dipakai:
    echo       Username : !ADMIN_USERNAME!
    echo       Password : !ADMIN_PASSWORD!
    echo       Login    : http://127.0.0.1:8000/login/
    echo       Admin    : http://127.0.0.1:8000/admin/
    echo       Disarankan mengganti kata sandi setelah login pertama.
)
echo   Login contoh (bila data contoh diisi): user1 / password123
echo ======================================================================
echo.
call :jeda
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


REM ══════════════════════════════════════════════════════════════════════
REM  Subrutin: tanyakan data contoh (aman untuk otomatisasi)
REM  - dijalankan manusia  : bertanya y/N
REM  - masukan dialihkan   : memakai baris masukan yang ada (launcher: "y")
REM  - tanpa masukan / EOF : otomatis "tidak" (script tidak menggantung)
REM ══════════════════════════════════════════════════════════════════════
:tanya_data
"%VENV_PY%" scripts\prompt_yes_no.py --pertanyaan "      Isi data contoh - 5 user + buku? [y/N]: " --bawaan n --output "%TEMP%\hirunaza_seed.txt"
if exist "%TEMP%\hirunaza_seed.txt" (
    set /p "ISI_DATA="<"%TEMP%\hirunaza_seed.txt"
    del "%TEMP%\hirunaza_seed.txt" >nul 2>&1
)
exit /b 0


REM ══════════════════════════════════════════════════════════════════════
REM  Subrutin: jeda (pause) yang bisa dilewati untuk otomatisasi
REM  Lewati dengan:  setup.bat /nopause   atau   set SETUP_NO_PAUSE=1
REM ══════════════════════════════════════════════════════════════════════
:jeda
if defined SETUP_NO_PAUSE exit /b 0
pause
exit /b 0
