@echo off
setlocal enabledelayedexpansion
title Build EXE Panel Kendali - Home Library
cd /d "%~dp0"

echo ============================================================
echo   BUILD .EXE "PANEL KENDALI"  (Home Library)
echo ============================================================
echo   Menghasilkan : home_library.exe
echo   Sumber       : launcher.py  (GUI tkinter)
echo ============================================================
echo.

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
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

REM  Catatan: .venv dibuat oleh uv dan TIDAK punya pip ("No module named pip"),
REM  jadi pemeriksaan/pemasangan PyInstaller tidak boleh bersandar pada pip.
REM  Pakai `python -c "import PyInstaller"` untuk memeriksa, dan uv untuk memasang.
echo   [1/4] Memastikan PyInstaller tersedia ...
"%VENV_PY%" -c "import PyInstaller" >nul 2>&1
if not errorlevel 1 (
    echo         sudah tersedia.
) else (
    echo         belum ada - memasang PyInstaller ...
    where uv >nul 2>&1
    if not errorlevel 1 (
        uv pip install --python "%VENV_PY%" pyinstaller
    ) else (
        "%VENV_PY%" -m pip install pyinstaller
    )
    "%VENV_PY%" -c "import PyInstaller" >nul 2>&1
    if errorlevel 1 (
        echo   [!] Gagal memasang PyInstaller. Periksa koneksi internet.
        pause
        exit /b 1
    )
)

REM ---------------------------------------------------------------------------
REM  PENTING (jangan diubah tanpa alasan):
REM  PyInstaller GAGAL bila folder tujuan mengandung SPASI. Gejalanya:
REM      FileNotFoundError / [Errno 22] Invalid argument
REM      ... dist\home_library.exe
REM  padahal folder tujuan normal bila diuji manual. Penyebabnya langkah
REM  "set_exe_build_timestamp" di PyInstaller yang menulis ganda backslash
REM  pada jalur berspasi (mis. "D:\IT Projects\...").
REM  Solusi: build di folder sementara TANPA spasi, lalu salin hasilnya ke sini.
REM ---------------------------------------------------------------------------
set "BUILD_DIR=%LOCALAPPDATA%\Temp\home_library_build"
set "EXE=%BUILD_DIR%\dist\home_library.exe"

echo   [2/4] Membersihkan folder build sementara ...
rmdir /s /q "%BUILD_DIR%" 2>nul
mkdir "%BUILD_DIR%" 2>nul

echo   [3/4] Membangun .exe (perlu 1-3 menit) ...
".venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm --onefile --windowed ^
    --name "home_library" ^
    --distpath "%BUILD_DIR%\dist" ^
    --workpath "%BUILD_DIR%\work" ^
    --specpath "%BUILD_DIR%" ^
    launcher.py

if not exist "%EXE%" (
    echo.
    echo   [!] Build GAGAL - .exe tidak terbentuk.
    echo       Coba jalankan build dari folder tanpa spasi, mis. C:\home_library
    echo.
    pause
    exit /b 1
)

echo   [4/4] Menyalin .exe ke folder aplikasi ...
rem .exe lama (nama sebelumnya) dibuang supaya tidak ada dua launcher
if exist "HirunazaLibraryLauncher.exe" del /q "HirunazaLibraryLauncher.exe" >nul 2>&1
copy /y "%EXE%" "home_library.exe" >nul
if errorlevel 1 (
    echo   [!] Gagal menyalin .exe ke folder ini.
    pause
    exit /b 1
)

echo.
echo   Uji cepat .exe ...
"home_library.exe" --selftest >nul 2>&1
if exist "selftest_launcher.txt" (
    findstr /c:"HASIL" selftest_launcher.txt
    del /q selftest_launcher.txt >nul 2>&1
)

echo.
echo ============================================================
echo   SELESAI.  .exe siap:  home_library.exe
echo.
echo   Cara pakai (untuk pengguna awam):
echo     1. Klik dua kali home_library.exe
echo     2. Klik "1. Siapkan"  (sekali saja)
echo     3. Klik "2. Jalankan" (browser terbuka sendiri)
echo     4. Isi nama pengguna + kata sandi lalu klik "Buat akun admin"
echo     5. Klik "3. Hentikan" kalau sudah selesai
echo ============================================================
echo.
pause
