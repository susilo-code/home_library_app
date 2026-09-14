@echo off
setlocal enabledelayedexpansion
title Build EXE Panel Kendali - Hirunaza Library
cd /d "%~dp0"

echo ============================================================
echo   BUILD .EXE "PANEL KENDALI"  (Hirunaza Library)
echo ============================================================
echo   Menghasilkan : HirunazaLibraryLauncher.exe
echo   Sumber       : launcher.py  (GUI tkinter)
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo   [!] Folder .venv belum ada.
    echo       Jalankan setup.bat terlebih dahulu.
    echo.
    pause
    exit /b 1
)

if not exist "launcher.py" (
    echo   [!] launcher.py tidak ditemukan di folder ini.
    echo.
    pause
    exit /b 1
)

echo   [1/4] Memastikan PyInstaller tersedia ...
".venv\Scripts\python.exe" -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo         memasang PyInstaller ...
    ".venv\Scripts\python.exe" -m pip install pyinstaller
    if errorlevel 1 (
        echo   [!] Gagal memasang PyInstaller. Periksa koneksi internet.
        pause
        exit /b 1
    )
) else (
    echo         sudah tersedia.
)

REM ---------------------------------------------------------------------------
REM  PENTING (jangan diubah tanpa alasan):
REM  PyInstaller GAGAL bila folder tujuan mengandung SPASI. Gejalanya:
REM      FileNotFoundError / [Errno 22] Invalid argument
REM      ... dist\HirunazaLibraryLauncher.exe
REM  padahal folder tujuan normal bila diuji manual. Penyebabnya langkah
REM  "set_exe_build_timestamp" di PyInstaller yang menulis ganda backslash
REM  pada jalur berspasi (mis. "D:\IT Projects\...").
REM  Solusi: build di folder sementara TANPA spasi, lalu salin hasilnya ke sini.
REM ---------------------------------------------------------------------------
set "BUILD_DIR=%LOCALAPPDATA%\Temp\hirunaza_launcher_build"
set "EXE=%BUILD_DIR%\dist\HirunazaLibraryLauncher.exe"

echo   [2/4] Membersihkan folder build sementara ...
rmdir /s /q "%BUILD_DIR%" 2>nul
mkdir "%BUILD_DIR%" 2>nul

echo   [3/4] Membangun .exe (perlu 1-3 menit) ...
".venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm --onefile --windowed ^
    --name "HirunazaLibraryLauncher" ^
    --distpath "%BUILD_DIR%\dist" ^
    --workpath "%BUILD_DIR%\work" ^
    --specpath "%BUILD_DIR%" ^
    launcher.py

if not exist "%EXE%" (
    echo.
    echo   [!] Build GAGAL - .exe tidak terbentuk.
    echo       Coba jalankan build dari folder tanpa spasi, mis. C:\hirunaza
    echo.
    pause
    exit /b 1
)

echo   [4/4] Menyalin .exe ke folder aplikasi ...
copy /y "%EXE%" "HirunazaLibraryLauncher.exe" >nul
if errorlevel 1 (
    echo   [!] Gagal menyalin .exe ke folder ini.
    pause
    exit /b 1
)

echo.
echo   Uji cepat .exe ...
"HirunazaLibraryLauncher.exe" --selftest >nul 2>&1
if exist "selftest_launcher.txt" (
    findstr /c:"HASIL" selftest_launcher.txt
    del /q selftest_launcher.txt >nul 2>&1
)

echo.
echo ============================================================
echo   SELESAI.  .exe siap:  HirunazaLibraryLauncher.exe
echo.
echo   Cara pakai (untuk pengguna awam):
echo     1. Klik dua kali HirunazaLibraryLauncher.exe
echo     2. Klik "1. Siapkan"  (sekali saja)
echo     3. Klik "2. Jalankan" (browser terbuka sendiri)
echo     4. Klik "3. Hentikan" kalau sudah selesai
echo ============================================================
echo.
pause
