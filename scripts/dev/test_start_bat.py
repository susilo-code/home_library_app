# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Uji start.bat: jalankan, pantau kesiapan Django (8000) & FastAPI (8001), lalu bersihkan.
Jalankan: .venv\\Scripts\\python.exe test_start_bat.py
"""
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / '_start_bat_test.log'


def listening(port: int) -> bool:
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout
    return any(f':{port} ' in line and 'LISTENING' in line for line in out.splitlines())


# ── Pengaman: script ini menjalankan stop.bat di akhir, jadi JANGAN sampai
#    mematikan service yang sedang dipakai pengguna. ────────────────────────
_terpakai = [p for p in (8000, 8001) if listening(p)]
if _terpakai and '--force' not in sys.argv:
    print("=" * 70)
    print(f"  DIBATALKAN: port {', '.join(str(p) for p in _terpakai)} sedang dipakai.")
    print("  Aplikasi sepertinya sedang berjalan (mungkin sedang Anda pakai).")
    print("  Script ini menguji start.bat + stop.bat, artinya service akan dimatikan.")
    print("  Hentikan dulu lewat stop.bat, atau jalankan: --force")
    print("=" * 70)
    sys.exit(2)


def kill_ports(*ports: int) -> int:
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout
    pids = {line.split()[-1] for line in out.splitlines()
            if 'LISTENING' in line and any(f':{p} ' in line for p in ports)}
    for pid in pids:
        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
    return len(pids)


def http(url: str, timeout: float = 3.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:
        return None, str(e)


print('=== 0. Bersihkan port 8000 & 8001 ===')
print(f'    proses dimatikan: {kill_ports(8000, 8001)}')
time.sleep(1)
print(f'    8000 LISTENING={listening(8000)}  8001 LISTENING={listening(8001)}')

print()
print('=== 1. Jalankan start.bat nobrowser ===')
logf = open(LOG, 'w', encoding='utf-8')
proc = subprocess.Popen(
    'cmd /c "start.bat nobrowser < nul"',
    shell=True, cwd=str(ROOT), stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
)
print(f'    PID launcher: {proc.pid}')

print()
print('=== 2. Pantau kesiapan service (maks 45 detik) ===')
django_up = fastapi_up = False
for i in range(15):
    time.sleep(3)
    if not django_up:
        django_up = listening(8000)
    if not fastapi_up:
        fastapi_up = listening(8001)
    print(f'    t+{(i+1)*3:2d}s  Django:{"UP" if django_up else ".."}  FastAPI:{"UP" if fastapi_up else ".."}')
    if django_up and fastapi_up:
        break

print()
print('=== 3. Uji HTTP lewat kedua service ===')
s, body = http('http://127.0.0.1:8000/login/')
print(f'    Django  /login/      -> HTTP {s}  (judul Hirunaza: {"Hirunaza" in body})')
s, body = http('http://127.0.0.1:8000/')
print(f'    Django  /            -> HTTP {s}  (redirect ke login = benar)')
s, body = http('http://127.0.0.1:8001/api/health')
print(f'    FastAPI /api/health  -> HTTP {s}  {body[:120]}')
s, body = http('http://127.0.0.1:8001/api/book-types')
print(f'    FastAPI /api/book-types -> HTTP {s}  {body[:120]}')
s, body = http('http://127.0.0.1:8001/api/stats')
print(f'    FastAPI /api/stats   -> HTTP {s}  (panjang {len(body)} char)')

print()
print('=== 4. Isi log start.bat ===')
print(LOG.read_text(encoding='utf-8', errors='replace'))

print('=== 5. Jalankan stop.bat ===')
r = subprocess.run('cmd /c "stop.bat < nul"', shell=True, cwd=str(ROOT),
                   capture_output=True, text=True, timeout=60)
print(r.stdout[-800:])
time.sleep(2)
print(f'    Setelah stop -> 8000 LISTENING={listening(8000)}  8001 LISTENING={listening(8001)}')

# pastikan bersih
kill_ports(8000, 8001)
print(f'    Final bersih -> 8000={listening(8000)}  8001={listening(8001)}')
