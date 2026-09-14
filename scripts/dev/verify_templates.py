# Bootstrap: pastikan root project ada di sys.path & working dir
import os as _os
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parents[2]
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
_os.chdir(_ROOT)

"""
Verifikasi template & halaman Home Library App.
Jalankan: .venv/Scripts/python.exe verify_templates.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.template.loader import get_template
from django.test import Client

TEMPLATES = [
    "base.html",
    "dashboard.html",
    "books/book_list.html",
    "books/book_form.html",
    "books/book_detail.html",
    "books/book_confirm_delete.html",
    "accounts/profile.html",
    "accounts/profile_form.html",
    "accounts/settings.html",
    "registration/login.html",
]

print("=== 1. COMPILE SEMUA TEMPLATE ===")
ok_all = True
for t in TEMPLATES:
    try:
        get_template(t)
        print(f"  [OK]   {t}")
    except Exception as e:
        ok_all = False
        print(f"  [GAGAL] {t} -> {type(e).__name__}: {e}")
print(f"\nHasil compile: {'SEMUA OK' if ok_all else 'ADA YANG GAGAL'}\n")

print("=== 2. TES RENDER HALAMAN (login user1) ===")
c = Client()
logged_in = c.login(username="user1", password="password123")
print(f"  Login user1/password123: {logged_in}\n")

PAGES = [
    ("/", "Dashboard", ["Distribusi Buku per Genre", "clock-time", "genreChart"]),
    ("/buku/", "Katalog Buku", ["Katalog Buku", "Terapkan Filter"]),
    ("/buku/tambah/", "Form Tambah Buku", ["Judul Buku", "Status Baca"]),
    ("/profil/", "Profil", ["Statistik Anda"]),
    ("/profil/edit/", "Edit Profil", ["Bio / Tentang Saya"]),
    ("/pengaturan/", "Pengaturan", ["Preferensi Tema"]),
]

for url, nama, penanda in PAGES:
    r = c.get(url)
    html = r.content.decode("utf-8", errors="replace")
    tanda = [p for p in penanda if p in html]
    status = "OK" if r.status_code == 200 else "GAGAL"
    print(f"  [{status}] {url:20s} {nama:20s} HTTP {r.status_code}  penanda={len(tanda)}/{len(penanda)}")
    if r.status_code != 200:
        print(f"        -> error snippet: {html[:300]}")

print("\n=== 3. TES WARNING DUPLIKASI JUDUL ===")
from library.forms import BookForm
from library.models import Book

existing = Book.objects.first()
if existing:
    form = BookForm(data={
        "title": existing.title,
        "author": existing.author,
        "genre": existing.genre_id,
        "status": "UNREAD",
        "rating": 5,
    })
    valid = form.is_valid()
    print(f"  Buku contoh: '{existing.title}' oleh {existing.author}")
    print(f"  Form valid (tidak diblokir): {valid}")
    if form.duplicate_warning:
        print(f"  Warning muncul: {form.duplicate_warning[:180]}...")
    else:
        print("  [GAGAL] Warning duplikasi TIDAK muncul")

print("\n=== 4. TES VALIDASI ISBN / TAHUN ===")
f2 = BookForm(data={
    "title": "Buku Uji Validasi", "author": "Penulis Uji",
    "genre": existing.genre_id if existing else 1,
    "status": "UNREAD", "rating": 5,
    "isbn": "12345", "publication_year": 2099,
})
f2.is_valid()
print(f"  ISBN '12345'          -> {f2.errors.get('isbn', ['(tidak ada error)'])[0]}")
print(f"  Tahun 2099            -> {f2.errors.get('publication_year', ['(tidak ada error)'])[0]}")
