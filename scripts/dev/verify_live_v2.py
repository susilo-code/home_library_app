# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""E2E ke server live: login ber-styling + semua halaman baru."""
import http.cookiejar
import re
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def get(url):
    return opener.open(BASE + url)


# ── 1. Halaman login baru ──────────────────────────────────────────────────
html = get("/login/").read().decode()
print("=== HALAMAN LOGIN ===")
print(f"  <title>            : {re.search(r'<title>(.*?)</title>', html).group(1)}")
print(f"  Judul sistem tampil: {'Hirunaza' in html and 'Library Information System' in html}")
print(f"  Gambar perpustakaan: {'library-hero.svg' in html}")
print(f"  Input ber-class    : {'placeholder-purple-200/50' in html}")
inputs = re.findall(r'<input type="(?:text|password)"[^>]*id="(id_\w+)"', html)
print(f"  Field login        : {inputs}")

# ── 2. Cek aset gambar bisa diakses ────────────────────────────────────────
r = get("/static/img/library-hero.svg")
data = r.read()
print(f"\n=== ASET GAMBAR ===")
print(f"  GET /static/img/library-hero.svg -> HTTP {r.status}  {len(data)} bytes  content-type={r.headers.get('Content-Type')}")

# ── 3. Login lewat /login/ (form ber-styling) ──────────────────────────────
token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
data = urllib.parse.urlencode({
    "username": os.environ.get("LIB_USER", "user1"),
    "password": os.environ.get("LIB_PASS", "password123"), "csrfmiddlewaretoken": token,
}).encode()
req = urllib.request.Request(BASE + "/login/", data=data, headers={"Referer": BASE + "/login/"})
resp = opener.open(req)
print(f"\n=== LOGIN ===")
print(f"  POST /login/ -> HTTP {resp.status}  final: {resp.url}")

# ── 4. Semua halaman ──────────────────────────────────────────────────────
PAGES = [
    ("/", "Dashboard", "Distribusi Buku per Genre"),
    ("/buku/", "Katalog Buku", "Jenis Buku"),
    ("/buku/tambah/", "Form Tambah Buku", "Lokasi Rak Buku"),
    ("/pengaturan/", "Pengaturan", "Genre / Kategori"),
    ("/pengaturan/genre/tambah/", "Form Genre", "Nama Genre / Kategori"),
    ("/pengaturan/rak/tambah/", "Form Rak", "Nama Lokasi Rak"),
    ("/profil/", "Profil", "Statistik Anda"),
    ("/password-change/", "Ubah Kata Sandi", "Kata Sandi"),
    ("/api/stats/", "API Stats", "shelf_distribution"),
]
print(f"\n=== HALAMAN (status HTTP + penanda) ===")
for url, nama, penanda in PAGES:
    try:
        r = get(url)
        body = r.read().decode("utf-8", errors="replace")
        status = r.status
    except urllib.error.HTTPError as e:
        status, body = e.code, ""
    ok = status == 200 and penanda in body
    print(f"  [{'OK' if ok else 'GAGAL'}] {url:26s} {nama:20s} HTTP {status}  '{penanda}'={'ada' if penanda in body else 'TIDAK'}")

# ── 5. Autocomplete judul lewat HTTP ──────────────────────────────────────
import json
r = get("/api/titles/?q=" + urllib.parse.quote("laskar"))
d = json.loads(r.read().decode())
print(f"\n=== AUTOCOMPLETE (live) ===")
print(f"  query='laskar' -> {len(d['results'])} saran, exact_match={d['exact_match']}")
for it in d["results"][:4]:
    print(f"    - {it['title']} | {it['author']} | mirip {int(it['similarity']*100)}% | exact={it['exact']} | rak={it['shelf'] or '-'}")

# ── 6. Cek redirect tautan lama ────────────────────────────────────────────
try:
    r = get("/accounts/login/")
    print(f"\n  /accounts/login/ -> HTTP {r.status} final: {r.url}")
except urllib.error.HTTPError as e:
    print(f"\n  /accounts/login/ -> HTTP {e.code}")
