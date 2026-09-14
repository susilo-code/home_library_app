# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""E2E check ke server live: login + akses semua halaman."""
import http.cookiejar
import re
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

# 1. Ambil halaman login + CSRF token
html = opener.open(f"{BASE}/accounts/login/").read().decode()
token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
print(f"CSRF token diambil: {token[:16]}...")

# 2. Login
data = urllib.parse.urlencode({
    "username": "user1",
    "password": "password123",
    "csrfmiddlewaretoken": token,
}).encode()
req = urllib.request.Request(f"{BASE}/accounts/login/", data=data,
                             headers={"Referer": f"{BASE}/accounts/login/"})
resp = opener.open(req)
print(f"Login -> HTTP {resp.status}  final URL: {resp.url}")

# 3. Cek halaman
PAGES = [
    ("/", "Dashboard", "Distribusi Buku per Genre"),
    ("/buku/", "Katalog", "Katalog Buku"),
    ("/buku/tambah/", "Form Buku", "Judul Buku"),
    ("/profil/", "Profil", "Statistik Anda"),
    ("/pengaturan/", "Pengaturan", "Preferensi Tema"),
    ("/api/stats/", "API Stats (JSON)", "genre_distribution"),
]
print()
for url, nama, penanda in PAGES:
    r = opener.open(f"{BASE}{url}")
    body = r.read().decode("utf-8", errors="replace")
    found = penanda in body
    print(f"  [{'OK' if r.status == 200 and found else 'GAGAL'}] {url:16s} {nama:18s} HTTP {r.status}  '{penanda}'={'ada' if found else 'TIDAK ADA'}")

# 4. Cek halaman detail buku
r = opener.open(f"{BASE}/buku/1/")
b = r.read().decode()
print(f"\n  [{'OK' if r.status == 200 else 'GAGAL'}] /buku/1/         Detail Buku        HTTP {r.status}  'oleh'={'ada' if 'oleh ' in b else 'TIDAK'}")

# 5. Cek 404 page not found
try:
    opener.open(f"{BASE}/buku/99999/")
except urllib.error.HTTPError as e:
    print(f"  [OK] /buku/99999/      Not Found          HTTP {e.code} (sesuai harapan)")
