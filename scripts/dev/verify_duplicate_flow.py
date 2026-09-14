# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""E2E test alur warning duplikasi judul buku via server live."""
import http.cookiejar
import os
import re
import urllib.error
import urllib.parse
import urllib.request

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from library.models import Book  # noqa: E402

BASE = "http://127.0.0.1:8000"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def get_csrf(url):
    html = opener.open(url).read().decode()
    return re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)


def post(url, payload, csrf):
    payload["csrfmiddlewaretoken"] = csrf
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Referer": url})
    return opener.open(req)


# Login — kredensial bisa dioverride lewat env (username bisa diganti dari panel admin)
LOGIN_USER = os.environ.get("LIB_USER", "user1")
LOGIN_PASS = os.environ.get("LIB_PASS", "password123")

csrf = get_csrf(f"{BASE}/login/")
post(f"{BASE}/login/", {"username": LOGIN_USER, "password": LOGIN_PASS}, csrf)
print(f"Login sebagai '{LOGIN_USER}': OK")
print("(bila gagal, set kredensial:  LIB_USER=namamu LIB_PASS=sandimu)\n")

existing = Book.objects.first()
print(f"Buku yang sudah ada: '{existing.title}' oleh {existing.author}")
before = Book.objects.count()
print(f"Jumlah buku sebelum: {before}\n")

# ── TES 1: submit duplikat TANPA konfirmasi ────────────────────────────────
csrf = get_csrf(f"{BASE}/buku/tambah/")
r = post(f"{BASE}/buku/tambah/", {
    "title": existing.title,
    "author": existing.author,
    "genre": str(existing.genre_id),
    "status": "UNREAD",
    "rating": "4",
}, csrf)
html = r.read().decode()
after1 = Book.objects.count()
print("TES 1 - Submit duplikat tanpa konfirmasi:")
print(f"  HTTP {r.status} (200 = form dirender ulang, bukan redirect)")
print(f"  Warning duplikasi tampil : {'YA' if 'sudah pernah diinput' in html else 'TIDAK'}")
print(f"  Tombol konfirmasi tampil : {'YA' if 'Tetap Simpan Buku Ini' in html else 'TIDAK'}")
print(f"  Buku tersimpan? count {before} -> {after1}  {'(TIDAK tersimpan - benar)' if after1 == before else '(TERSIMPAN - salah!)'}\n")

# ── TES 2: submit duplikat DENGAN konfirmasi (_ignore_duplicate) ───────────
csrf = get_csrf(f"{BASE}/buku/tambah/")
r = post(f"{BASE}/buku/tambah/", {
    "title": existing.title,
    "author": existing.author,
    "genre": str(existing.genre_id),
    "status": "COMPLETED",
    "rating": "5",
    "_ignore_duplicate": "1",
}, csrf)
after2 = Book.objects.count()
print("TES 2 - Submit duplikat dengan konfirmasi (_ignore_duplicate=1):")
print(f"  HTTP {r.status}  final URL: {r.url}")
print(f"  Buku tersimpan? count {after1} -> {after2}  {'(TERSIMPAN - benar)' if after2 == after1 + 1 else '(TIDAK tersimpan - salah!)'}")

# Bersihkan duplikat uji coba
if after2 > after1:
    dupe = Book.objects.filter(title=existing.title, author=existing.author).order_by("-id").first()
    dupe.delete()
    print(f"\nBersih-bersih: buku uji dihapus, count kembali ke {Book.objects.count()}")

# ── TES 3: submit buku BARU (tidak duplikat) ───────────────────────────────
before3 = Book.objects.count()
csrf = get_csrf(f"{BASE}/buku/tambah/")
r = post(f"{BASE}/buku/tambah/", {
    "title": "Buku Unik Uji Coba 2026",
    "author": "Penulis Unik Uji",
    "genre": str(existing.genre_id),
    "status": "UNREAD",
    "rating": "3",
}, csrf)
after3 = Book.objects.count()
created3 = Book.objects.filter(title="Buku Unik Uji Coba 2026").exists()
print("\nTES 3 - Submit buku baru (tidak duplikat):")
print(f"  HTTP {r.status}  final URL: {r.url}  {'(redirect ke daftar - benar)' if r.url.endswith('/buku/') else ''}")
print(f"  Buku tersimpan di DB? {created3}   count {before3} -> {after3}  {'(TERSIMPAN - benar)' if after3 == before3 + 1 else '(TIDAK tersimpan - salah!)'}")
if created3:
    Book.objects.filter(title="Buku Unik Uji Coba 2026").delete()
    print(f"\nBersih-bersih: count kembali ke {Book.objects.count()}")

print(f"\nTotal buku di database sekarang: {Book.objects.count()}")
print(f"Sisa buku uji: {Book.objects.filter(title__startswith='Buku Unik Uji').count()}")
