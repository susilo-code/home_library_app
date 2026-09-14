# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Uji daur hidup start.bat -> stop.bat:
  1. start.bat menjalankan Django (8000) + FastAPI (8001)
  2. kedua endpoint merespons HTTP 200
  3. stop.bat mematikan KEDUA service
  4. stop.bat juga menutup jendela launcher (tidak menumpuk lagi)

Jalankan: .venv\\Scripts\\python.exe scripts\\dev\\verify_start_stop_cycle.py
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / '_cycle_start.log'
hasil = []


def cek(nama, kondisi, detail=""):
    hasil.append(bool(kondisi))
    print(f"  {'[OK]  ' if kondisi else '[GAGAL]'} {nama}{(' — ' + detail) if detail else ''}")


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout
    return any(f':{port} ' in l and 'LISTENING' in l for l in out.splitlines())


# ── Pengaman: script ini menguji start.bat + stop.bat, jadi JANGAN sampai
#    mematikan service yang sedang dipakai pengguna. ────────────────────────
_terpakai = [p for p in (8000, 8001) if listening(p)]
if _terpakai and '--force' not in sys.argv:
    print("=" * 70)
    print(f"  DIBATALKAN: port {', '.join(str(p) for p in _terpakai)} sedang dipakai.")
    print("  Aplikasi sepertinya sedang berjalan (mungkin sedang Anda pakai).")
    print("  Hentikan dulu lewat stop.bat, atau jalankan: --force")
    print("=" * 70)
    sys.exit(2)


def launcher_windows():
    ps = subprocess.run(['powershell', '-NoProfile', '-Command',
                         "Get-CimInstance Win32_Process -Filter \"Name='cmd.exe'\" | "
                         "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],
                        capture_output=True, text=True)
    try:
        data = json.loads(ps.stdout or '[]')
    except Exception:
        return []
    if isinstance(data, dict):
        data = [data]
    return [p for p in data if 'home_library_app' in (p.get('CommandLine') or '')]


def http(url, timeout=4):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:
        return None, str(e)


def jalankan_bat(nama, extra=""):
    """Jalankan .bat dengan output ke file (bukan pipe) agar tidak menggantung."""
    logf = open(ROOT / f'_cycle_{nama}.log', 'w', encoding='utf-8')
    p = subprocess.Popen(f'cmd /c "{nama} {extra} < nul"', shell=True, cwd=str(ROOT),
                         stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    return p, logf


print('═' * 74)
print('  UJI DAUR HIDUP start.bat -> stop.bat')
print('═' * 74)

# Bersihkan dulu
subprocess.run(f'cmd /c "stop.bat < nul"', shell=True, cwd=str(ROOT), capture_output=True)
time.sleep(2)
print(f"\n  Kondisi awal: 8000={listening(8000)} 8001={listening(8001)} "
      f"launcher={len(launcher_windows())}")

print('\n>>> 1. Jalankan start.bat nobrowser')
proc, logf = jalankan_bat('start.bat', 'nobrowser')
siap = False
for _ in range(20):
    time.sleep(3)
    if listening(8000) and listening(8001):
        siap = True
        break
cek("Django (8000) berjalan", listening(8000))
cek("FastAPI (8001) berjalan", listening(8001))
cek("Jendela launcher bertambah", len(launcher_windows()) >= 2, f"{len(launcher_windows())} jendela")

print('\n>>> 2. Uji endpoint kedua service')
if siap:
    s, b = http('http://127.0.0.1:8000/login/')
    cek("Django /login/ HTTP 200", s == 200 and 'Hirunaza' in b, f"HTTP {s}")
    s, b = http('http://127.0.0.1:8001/api/health')
    cek("FastAPI /api/health HTTP 200", s == 200 and 'ok' in b, f"HTTP {s}")
    s, b = http('http://127.0.0.1:8001/api/book-types')
    cek("FastAPI /api/book-types HTTP 200", s == 200, f"HTTP {s}")
else:
    cek("Kedua service siap dalam 60 detik", False)

print('\n>>> 3. Jalankan stop.bat')
proc2, logf2 = jalankan_bat('stop.bat')
proc2.wait(timeout=90)
time.sleep(3)
logf2.close()
logf.close()          # lepaskan handle log launcher agar bisa dihapus
time.sleep(1)
cek("Django (8000) berhenti", not listening(8000))
cek("FastAPI (8001) berhenti", not listening(8001))
sisa = launcher_windows()
cek("Jendela launcher ikut tertutup (tidak menumpuk)", len(sisa) == 0,
    f"{len(sisa)} jendela tersisa" + (f" -> {[p['ProcessId'] for p in sisa]}" if sisa else ""))

print('\n>>> 4. Isi log stop.bat')
print((ROOT / '_cycle_stop.bat.log').read_text(encoding='utf-8', errors='replace')[-500:])

for f in ['_cycle_start.bat.log', '_cycle_stop.bat.log', '_cycle_start.log']:
    p = ROOT / f
    if p.exists():
        try:
            p.unlink()
        except Exception as e:
            print(f"  (tidak bisa hapus {f}: {e})")

print()
print('═' * 74)
total, ok = len(hasil), sum(hasil)
print(f"HASIL AKHIR: {ok}/{total} pemeriksaan LULUS" + (" — SEMUA BAIK ✅" if ok == total else f" — {total - ok} GAGAL ❌"))
print('═' * 74)
