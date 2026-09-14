@echo off
REM ══════════════════════════════════════════════════════════════════════
REM  push_github.bat — Kirim project ini ke GitHub
REM
REM  Pemakaian:
REM     push_github.bat
REM
REM  Sebelum menjalankan:
REM     1. Buat repository KOSONG di https://github.com/new
REM        (JANGAN centang "Add a README file" / .gitignore / license)
REM     2. Siapkan URL-nya, contoh:
REM        https://github.com/username/hirunaza-library.git
REM     3. Bila diminta sandi, gunakan Personal Access Token (PAT),
REM        bukan kata sandi akun GitHub Anda.
REM        Buat PAT: https://github.com/settings/tokens  (scope: repo)
REM ══════════════════════════════════════════════════════════════════════
setlocal EnableExtensions EnableDelayedExpansion
title Push ke GitHub - Hirunaza's Library
cd /d "%~dp0"

echo ======================================================================
echo   PUSH PROYEK KE GITHUB
echo ======================================================================
echo.

REM ── Pastikan git tersedia ────────────────────────────────────────────
where git >nul 2>&1
if !errorlevel! NEQ 0 (
    echo [X] Git tidak ditemukan. Install dari https://git-scm.com/downloads
    pause
    exit /b 1
)

REM ── Pastikan repo git sudah ada ──────────────────────────────────────
if not exist ".git" (
    echo [!] Belum ada repository git di folder ini - membuat sekarang...
    git init -q
    git branch -M main
)

REM ── Identitas commit ─────────────────────────────────────────────────
for /f "delims=" %%N in ('git config user.name') do set "GIT_NAME=%%N"
if "!GIT_NAME!"=="" (
    set /p "GIT_NAME=Masukkan nama Anda untuk commit: "
    git config user.name "!GIT_NAME!"
)
for /f "delims=" %%E in ('git config user.email') do set "GIT_EMAIL=%%E"
if "!GIT_EMAIL!"=="" (
    set /p "GIT_EMAIL=Masukkan email GitHub Anda: "
    git config user.email "!GIT_EMAIL!"
)
echo [i] Commit sebagai: !GIT_NAME! ^<!GIT_EMAIL!^>
echo.

REM ── Commit perubahan yang belum tersimpan ────────────────────────────
set "PERUBAHAN="
for /f "delims=" %%S in ('git status --porcelain') do set "PERUBAHAN=1"
if defined PERUBAHAN (
    set "PESAN="
    set /p "PESAN=Pesan commit (kosongkan untuk 'update: perubahan terbaru'): "
    REM buang spasi di ujung; pesan yang hanya berisi spasi dianggap kosong
    for /f "tokens=* delims= " %%P in ("!PESAN!") do set "PESAN=%%P"
    if "!PESAN!"=="" set "PESAN=update: perubahan terbaru"
    git add -A
    git commit -q -m "!PESAN!"
    if errorlevel 1 (
        echo [!] Commit gagal atau tidak ada perubahan yang bisa di-commit.
    ) else (
        echo [OK] Perubahan di-commit: "!PESAN!"
    )
) else (
    echo [i] Tidak ada perubahan baru untuk di-commit.
)
echo.

REM ── Atur / periksa remote ────────────────────────────────────────────
set "REMOTE_URL="
for /f "delims=" %%R in ('git remote get-url origin 2^>nul') do set "REMOTE_URL=%%R"

if "!REMOTE_URL!"=="" (
    echo Belum ada remote 'origin'.
    echo Contoh: https://github.com/username/hirunaza-library.git
    set /p "REMOTE_URL=Masukkan URL repository GitHub: "
    if "!REMOTE_URL!"=="" (
        echo [X] URL tidak boleh kosong.
        pause
        exit /b 1
    )
    git remote add origin "!REMOTE_URL!"
    echo [OK] Remote origin diset: !REMOTE_URL!
) else (
    echo [i] Remote origin sudah ada: !REMOTE_URL!
)
echo.

REM ── Push ─────────────────────────────────────────────────────────────
echo Mengirim ke GitHub (branch main)...
git branch -M main
git push -u origin main
if errorlevel 1 (
    echo.
    echo [X] Push gagal. Kemungkinan penyebab:
    echo     - URL repository salah / belum dibuat di GitHub
    echo     - Perlu login: gunakan Personal Access Token sebagai sandi
    echo       ^(https://github.com/settings/tokens^)
    echo     - Repository di GitHub sudah berisi file ^(buat yang benar-benar kosong^)
    echo     - Riwayat berbeda: jalankan  git pull --rebase origin main  lalu ulangi
    echo.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo   BERHASIL DI-PUSH
echo ======================================================================
for /f "delims=" %%U in ('git remote get-url origin') do echo   Repository: %%U
echo   Branch    : main
echo   Commit    : 
git log --oneline -1
echo.
echo   Clone di PC lain:
echo     git clone ^<URL di atas^>
echo     lalu jalankan setup.bat dan start.bat
echo ======================================================================
echo.
pause
