"""
Uji skenario PC BARU: clone bersih dari repo git -> venv baru -> setup -> jalankan.

Tujuannya memastikan MANUAL.md benar-benar bekerja: tidak ada dependency yang
tertinggal, .env bisa dibuat, migrasi & seeder jalan, aplikasi bisa boot.

Jalankan: .venv\\Scripts\\python.exe scripts\\dev\\verify_fresh_clone.py
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = Path(tempfile.gettempdir()) / 'hirunaza_clone_test'
PORT = 8099
PY = None  # diisi setelah venv dibuat

langkah_gagal = []


def jalankan(cmd, cwd, label, timeout=900, env=None):
    print(f'\n>>> {label}')
    print(f'    $ {" ".join(str(c) for c in cmd)}')
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       timeout=timeout, env=env)
    keluaran = (r.stdout or '') + (r.stderr or '')
    for baris in keluaran.strip().splitlines()[-6:]:
        print(f'      {baris}')
    if r.returncode != 0:
        langkah_gagal.append(label)
        print(f'    [GAGAL] exit={r.returncode}')
    else:
        print(f'    [OK]')
    return r


def port_bebas(port):
    with socket.socket() as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


def main():
    print('═' * 70)
    print('  UJI SKENARIO PC BARU — clone bersih + setup dari nol')
    print('═' * 70)
    print(f'Repo sumber : {ROOT}')
    print(f'Folder uji  : {TEST_DIR}')

    if TEST_DIR.exists():
        print('  (menghapus folder uji lama)')
        shutil.rmtree(TEST_DIR, ignore_errors=True)

    # 1. Clone bersih dari repo lokal
    jalankan(['git', 'clone', '--quiet', str(ROOT), str(TEST_DIR)],
             cwd=ROOT.parent, label='1. Clone bersih repo')

    # 2. Pastikan file rahasia TIDAK ikut ter-clone
    print('\n>>> 2. Cek berkas yang seharusnya tidak ikut ter-clone')
    for nama in ['.env', 'db.sqlite3', '.venv', 'node_modules']:
        ada = (TEST_DIR / nama).exists()
        status = '[GAGAL] ikut ter-clone' if ada else '[OK] tidak ada (benar)'
        if ada:
            langkah_gagal.append(f'berkas {nama} bocor')
        print(f'      {nama:14s} {status}')
    for nama in ['.env.example', 'requirements.txt', 'MANUAL.md', 'start.bat',
                 'static/css/output.css', 'library/migrations/0004_book_type_fixed_and_purchase_year.py']:
        ada = (TEST_DIR / nama).exists()
        if not ada:
            langkah_gagal.append(f'berkas {nama} hilang')
        print(f'      {nama:60s} {"ada" if ada else "[GAGAL] HILANG"}')

    # 3. Venv baru + dependency
    global PY
    uv = shutil.which('uv')
    if uv:
        jalankan([uv, 'venv', '.venv'], cwd=TEST_DIR, label='3a. Buat venv dengan uv')
    else:
        jalankan([sys.executable, '-m', 'venv', '.venv'], cwd=TEST_DIR, label='3a. Buat venv dengan venv')
    PY = TEST_DIR / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')

    if uv:
        jalankan([uv, 'pip', 'install', '--python', str(PY), '-r', 'requirements.txt'],
                 cwd=TEST_DIR, label='3b. Install requirements.txt (uv)')
    else:
        jalankan([str(PY), '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'],
                 cwd=TEST_DIR, label='3b. Install requirements.txt (pip)')

    # 4. Cek MODUL benar-benar bisa diimpor (bukti dependency lengkap)
    jalankan([str(PY), '-c',
              'import django, fastapi, uvicorn, dotenv, PIL, pydantic, multipart;'
              'print("semua modul inti OK | Django", django.get_version())'],
             cwd=TEST_DIR, label='4. Verifikasi dependency dapat diimpor')

    # 5. Buat .env
    jalankan([str(PY), 'scripts/init_env.py'], cwd=TEST_DIR, label='5. Buat .env + SECRET_KEY acak')
    env_file = TEST_DIR / '.env'
    if env_file.exists():
        isi = env_file.read_text(encoding='utf-8')
        ada_secret = 'SECRET_KEY=' in isi and 'GANTI-DENGAN' not in isi
        print(f'      .env dibuat, SECRET_KEY acak terisi: {ada_secret}')
        if not ada_secret:
            langkah_gagal.append('SECRET_KEY .env tidak diganti')
    else:
        langkah_gagal.append('.env tidak dibuat')
        print('      [GAGAL] .env tidak dibuat')

    # 6. Migrasi + seeder
    jalankan([str(PY), 'manage.py', 'migrate'], cwd=TEST_DIR, label='6a. Migrasi database')
    jalankan([str(PY), 'manage.py', 'seed_data', '--users', '2', '--books-per-user', '3'],
             cwd=TEST_DIR, label='6b. Seed data contoh', timeout=300)
    jalankan([str(PY), 'manage.py', 'check'], cwd=TEST_DIR, label='6c. Django check')

    # 7. Jalankan server & uji HTTP
    print('\n>>> 7. Menjalankan server hasil clone')
    log = open(TEST_DIR / 'server.log', 'w', encoding='utf-8')
    srv = subprocess.Popen([str(PY), 'manage.py', 'runserver', f'127.0.0.1:{PORT}', '--noreload'],
                           cwd=str(TEST_DIR), stdout=log, stderr=subprocess.STDOUT)
    siap = False
    for _ in range(12):
        time.sleep(2)
        if not port_bebas(PORT):
            siap = True
            break
    if siap:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/login/', timeout=5) as r:
                html = r.read().decode('utf-8', errors='replace')
            ok = r.status == 200 and 'Hirunaza' in html
            print(f'    [{"OK" if ok else "GAGAL"}] GET /login/ -> HTTP {r.status}, judul Hirunaza: {"Hirunaza" in html}')
            if not ok:
                langkah_gagal.append('halaman login gagal')
        except Exception as e:
            langkah_gagal.append(f'HTTP gagal: {e}')
            print(f'    [GAGAL] {e}')
    else:
        langkah_gagal.append('server tidak siap')
        print('    [GAGAL] server tidak siap dalam 24 detik')
        print((TEST_DIR / 'server.log').read_text(encoding='utf-8', errors='replace')[-800:])

    srv.terminate()
    log.close()
    time.sleep(1)

    print()
    print('═' * 70)
    if langkah_gagal:
        print(f'  HASIL: {len(langkah_gagal)} LANGKAH GAGAL')
        for l in langkah_gagal:
            print(f'    - {l}')
    else:
        print('  HASIL: SKENARIO PC BARU BERHASIL SEMUA ✅')
    print(f'  Folder uji dibiarkan untuk diperiksa: {TEST_DIR}')
    print('═' * 70)


if __name__ == '__main__':
    main()
